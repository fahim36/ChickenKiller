/** The Learner's colour theme: follow the system setting, or always Light or Dark. */
export type Theme = "system" | "light" | "dark";

export const THEME_COOKIE = "theme";

/** The Theme a cookie value names; anything else follows the system setting. */
export function parseTheme(value: string | undefined): Theme {
  return value === "light" || value === "dark" ? value : "system";
}

/** Applies a Theme at once and remembers it in a cookie, so the server renders it next time. */
export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
  document.cookie = `${THEME_COOKIE}=${theme}; path=/; max-age=31536000; samesite=lax`;
}
