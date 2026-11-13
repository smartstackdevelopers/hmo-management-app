# Production activation checklist

- [ ] Client written approval for Section 11 AI Voice Calling
- [ ] DPO privacy review for telephony
- [ ] `VOICE_CALLING_GLOBAL_ENABLED=true`
- [ ] Provider credentials in Secrets Manager (not Git)
- [ ] Webhook signing secret configured
- [ ] Organisation settings `enabled=true`
- [ ] Smoke test in staging with mock mode
- [ ] Twilio/live provider approval separate gate
- [ ] No production activation in F8.1 default config
