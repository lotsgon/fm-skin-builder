import { useTheme } from '@/components/theme-provider';

export function Logo({ className }: { className?: string }) {
  const { theme } = useTheme();

  // Determine if we're in dark mode (either explicitly dark or system preference is dark)
  const isDark = theme === 'dark' ||
    (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

  return (
    <div className={className}>
      {/* Placeholder SVG logo - can be replaced with actual logo from site-fm-skin-builder */}
      <svg
        width="32"
        height="32"
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect
          width="32"
          height="32"
          rx="6"
          fill={isDark ? "hsl(263 70% 50%)" : "hsl(262 83% 58%)"}
        />
        <path
          d="M10 12h12v2H10v-2zm0 4h12v2H10v-2zm0 4h8v2h-8v-2z"
          fill="white"
        />
      </svg>
    </div>
  );
}
