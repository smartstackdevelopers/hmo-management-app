import { theme } from '@/constants/theme';

function relativeLuminance(hex: string): number {
  const normalized = hex.replace('#', '');
  const channels = [0, 2, 4].map((i) => {
    const v = parseInt(normalized.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(foreground: string, background: string): number {
  const l1 = relativeLuminance(foreground);
  const l2 = relativeLuminance(background);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe('F7.5 mobile accessibility foundations', () => {
  it('primary button text meets contrast on brand background', () => {
    const ratio = contrastRatio(theme.colors.textInverse, theme.colors.primary);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  it('body text meets contrast on app background', () => {
    const ratio = contrastRatio(theme.colors.text, theme.colors.background);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });
});
