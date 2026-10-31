/** Plain-language labels — avoid jargon across the app. */
export const SIMPLE = {
  documents: {
    title: 'Documents',
    subtitle: 'Certificates, tenancy papers and uploads — tap any file to read it',
    upload: 'Add a file',
    export: 'Download certificate pack',
    empty: 'No files yet. Upload gas certificates, EPCs and tenancy agreements here.',
    actionNeeded: 'Needs attention',
    allGood: 'Up to date',
    allFiles: 'All files',
    tapOpen: 'Tap to read',
  },
  compliance: {
    title: 'Property checks',
    subtitle: 'Make sure your properties meet council rules',
    score: 'Overall score',
    whatToFix: 'What to fix',
    yourProperties: 'Your properties',
    allGood: 'Everything looks good. Keep your certificates up to date.',
    seeChecklist: 'Full checklist',
  },
  home: {
    todo: 'To do',
    updates: 'Recent updates',
    allCaughtUp: 'You\'re all caught up — nothing needs doing right now.',
    shortcuts: 'Quick actions',
  },
  account: {
    title: 'Account',
    notifications: 'Alerts',
    files: 'My files',
    password: 'Password',
    help: 'Get help',
    signOut: 'Sign out',
  },
} as const;
