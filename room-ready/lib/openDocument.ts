import * as WebBrowser from 'expo-web-browser';
import { Linking, Platform } from 'react-native';

import { getFileUrl } from '@/lib/config';

/** Open a stored document so the user can read it (HTML demos or PDFs). */
export async function openDocumentFile(fileUrl: string): Promise<void> {
  const url = getFileUrl(fileUrl);
  try {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined') {
        window.open(url, '_blank', 'noopener,noreferrer');
        return;
      }
    }
    await WebBrowser.openBrowserAsync(url, {
      presentationStyle: WebBrowser.WebBrowserPresentationStyle.PAGE_SHEET,
      controlsColor: '#0D9488',
    });
  } catch {
    await Linking.openURL(url);
  }
}
