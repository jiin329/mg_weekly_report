import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const stored = localStorage.getItem("theme");
    if (stored === "light" || stored === "dark") return stored;
    return "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  function toggle() {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }

  const nextThemeLabel = theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환";

  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      aria-label={nextThemeLabel}
      title={nextThemeLabel}
      type="button"
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
