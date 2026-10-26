// Подключить в tailwind.config.ts: theme.extend = tokens
const v = (n: string) => `var(--${n})`;
export const tokens = {
  colors: {
    bg: v('bg'), surface: v('surface'), 'surface-2': v('surface-2'),
    border: v('border'), 'border-input': v('border-input'),
    text: v('text'), muted: v('text-muted'),
    accent: v('accent'), 'on-accent': v('on-accent'),
    link: v('link'), 'link-missing': v('link-missing'),
    danger: v('danger'), success: v('success'), warning: v('warning'),
    ring: v('focus-ring'),
  },
  fontFamily: { sans: [v('font-sans')], mono: [v('font-mono')] },
  borderRadius: { sm: v('radius-sm'), md: v('radius-md'), lg: v('radius-lg') },
  boxShadow: { popover: v('shadow-popover'), modal: v('shadow-modal') },
};
