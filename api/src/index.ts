import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import path from 'path';

import authRoutes from './routes/auth';
import propertyRoutes from './routes/properties';
import listingRoutes from './routes/listings';
import applicationRoutes from './routes/applications';
import tenancyRoutes from './routes/tenancies';
import maintenanceRoutes from './routes/maintenance';
import documentRoutes from './routes/documents';
import messageRoutes from './routes/messages';
import notificationRoutes from './routes/notifications';
import inspectionRoutes from './routes/inspections';
import adminRoutes from './routes/admin';
import userRoutes from './routes/users';
import dashboardRoutes from './routes/dashboard';

const app = express();
const PORT = process.env.PORT ?? 3001;

app.use(cors());
app.use(express.json());
app.use('/uploads', express.static(path.resolve(process.env.UPLOAD_DIR ?? './uploads')));

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'Room Ready API', region: 'GB' });
});

app.use('/auth', authRoutes);
app.use('/properties', propertyRoutes);
app.use('/listings', listingRoutes);
app.use('/applications', applicationRoutes);
app.use('/tenancies', tenancyRoutes);
app.use('/maintenance', maintenanceRoutes);
app.use('/documents', documentRoutes);
app.use('/conversations', messageRoutes);
app.use('/notifications', notificationRoutes);
app.use('/inspections', inspectionRoutes);
app.use('/admin', adminRoutes);
app.use('/users', userRoutes);
app.use('/dashboard', dashboardRoutes);

app.use((_req, res) => {
  res.status(404).json({ error: 'Not found' });
});

app.listen(PORT, () => {
  console.log(`Room Ready API running on http://localhost:${PORT}`);
});
