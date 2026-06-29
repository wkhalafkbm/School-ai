"use client";

import { useEffect, useState } from "react";
import LoginForm from "./LoginForm";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    setAuthenticated(sessionStorage.getItem("authenticated") === "true");
  }, []);

  function handleLogin() {
    setAuthenticated(true);
  }

  if (authenticated === null) return null;
  if (!authenticated) return <LoginForm onLogin={handleLogin} />;
  return <>{children}</>;
}
