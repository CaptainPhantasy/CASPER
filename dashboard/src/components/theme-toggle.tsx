import { Moon, Sun } from "lucide-react";
import * as React from "react";

import { Switch } from "@/components/ui/switch";

export function ThemeToggle() {
  const [isDark, setIsDark] = React.useState(true);

  React.useEffect(() => {
    const saved = window.localStorage.getItem("casper-theme");
    if (saved === "light") {
      setIsDark(false);
      document.documentElement.classList.add("light");
    } else {
      setIsDark(true);
      document.documentElement.classList.remove("light");
    }
  }, []);

  const handleToggle = (value: boolean) => {
    setIsDark(value);
    if (!value) {
      document.documentElement.classList.add("light");
      window.localStorage.setItem("casper-theme", "light");
    } else {
      document.documentElement.classList.remove("light");
      window.localStorage.setItem("casper-theme", "dark");
    }
  };

  return (
    <div className="flex items-center space-x-2">
      <Sun className="h-4 w-4 text-muted-foreground" />
      <Switch checked={isDark} onCheckedChange={handleToggle} aria-label="Toggle theme" />
      <Moon className="h-4 w-4 text-muted-foreground" />
    </div>
  );
}
