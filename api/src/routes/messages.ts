import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);

const createConversationSchema = z.object({
  participantIds: z.array(z.string()).min(1),
  propertyId: z.string().optional(),
  subject: z.string().optional(),
  initialMessage: z.string().optional(),
});

const aiAssistSchema = z.object({
  mode: z.enum(['rewrite_professional', 'summarize']),
  text: z.string().min(1),
});

router.get('/', async (req, res) => {
  const { userId } = req.user!;

  const conversations = await prisma.conversation.findMany({
    where: {
      participants: { some: { userId } },
    },
    include: {
      participants: {
        include: { user: { select: { id: true, firstName: true, lastName: true, role: true } } },
      },
      messages: {
        orderBy: { createdAt: 'desc' },
        take: 1,
        include: { sender: { select: { id: true, firstName: true } } },
      },
      property: { select: { id: true, name: true } },
    },
    orderBy: { updatedAt: 'desc' },
  });

  res.json({ conversations });
});

router.post('/', async (req, res) => {
  const { userId } = req.user!;

  try {
    const data = createConversationSchema.parse(req.body);
    const allParticipants = [...new Set([userId, ...data.participantIds])];

    const conversation = await prisma.conversation.create({
      data: {
        propertyId: data.propertyId,
        subject: data.subject,
        participants: {
          create: allParticipants.map((id) => ({ userId: id })),
        },
      },
      include: {
        participants: {
          include: { user: { select: { id: true, firstName: true, lastName: true, role: true } } },
        },
      },
    });

    if (data.initialMessage) {
      await prisma.message.create({
        data: {
          conversationId: conversation.id,
          senderId: userId,
          body: data.initialMessage,
        },
      });
    }

    res.status(201).json({ conversation });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to create conversation' });
  }
});

router.get('/:id/messages', async (req, res) => {
  const { userId } = req.user!;
  const participant = await prisma.conversationParticipant.findUnique({
    where: {
      conversationId_userId: { conversationId: req.params.id, userId },
    },
  });
  if (!participant) return res.status(403).json({ error: 'Access denied' });

  const messages = await prisma.message.findMany({
    where: { conversationId: req.params.id },
    include: { sender: { select: { id: true, firstName: true, lastName: true } } },
    orderBy: { createdAt: 'asc' },
  });

  res.json({ messages });
});

router.post('/:id/messages', async (req, res) => {
  const { userId } = req.user!;
  const participant = await prisma.conversationParticipant.findUnique({
    where: {
      conversationId_userId: { conversationId: req.params.id, userId },
    },
  });
  if (!participant) return res.status(403).json({ error: 'Access denied' });

  const body = req.body.body as string;
  if (!body?.trim()) return res.status(400).json({ error: 'Message body required' });

  const message = await prisma.message.create({
    data: { conversationId: req.params.id, senderId: userId, body: body.trim() },
    include: { sender: { select: { id: true, firstName: true, lastName: true } } },
  });

  await prisma.conversation.update({
    where: { id: req.params.id },
    data: { updatedAt: new Date() },
  });

  const others = await prisma.conversationParticipant.findMany({
    where: { conversationId: req.params.id, userId: { not: userId } },
  });
  for (const p of others) {
    await prisma.notification.create({
      data: {
        userId: p.userId,
        type: 'message',
        title: 'New message',
        body: body.slice(0, 100),
        data: JSON.stringify({ conversationId: req.params.id }),
      },
    });
  }

  res.status(201).json({ message });
});

router.post('/ai-assist', async (req, res) => {
  try {
    const data = aiAssistSchema.parse(req.body);
    const text = data.text.trim();
    if (!text) return res.status(400).json({ error: 'Text is required' });

    if (data.mode === 'summarize') {
      const cleaned = text.replace(/\s+/g, ' ');
      const sentences = cleaned.split(/(?<=[.!?])\s+/).filter(Boolean);
      const summary = sentences.slice(0, 2).join(' ').slice(0, 280);
      return res.json({
        output:
          summary ||
          cleaned.slice(0, 280),
      });
    }

    const rewritten = text
      .replace(/\bi need\b/gi, 'I would like')
      .replace(/\basap\b/gi, 'as soon as possible')
      .replace(/\bpls\b/gi, 'please')
      .replace(/\s+/g, ' ')
      .trim();

    const output = rewritten.endsWith('.')
      ? `Hello,\n\n${rewritten}\n\nThank you,\nRoom Ready user`
      : `Hello,\n\n${rewritten}.\n\nThank you,\nRoom Ready user`;

    return res.json({ output });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    return res.status(500).json({ error: 'AI assist failed' });
  }
});

export default router;
