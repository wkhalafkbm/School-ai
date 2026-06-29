"use client";

import { useState } from "react";
import { getBrandingConfig } from "@/lib/brandingConfig";

export default function LoginForm({ onLogin }: { onLogin?: () => void }) {
  const { name, subtitle, logoUrl } = getBrandingConfig();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    sessionStorage.setItem("authenticated", "true");
    onLogin?.();
  }

  return (
    <div className="login-page">
      <div className="login-card">
        {logoUrl ? (
          <img src={logoUrl} alt="University logo" width={56} height={56} className="login-card__logo" />
        ) : (
          <span data-testid="logo-fallback" className="login-card__logo-fallback">Logo</span>
        )}
        <div className="login-card__heading">
          <span className="login-card__name">{name}</span>
          <span className="login-card__subtitle">{subtitle}</span>
        </div>
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-form__field">
            <label className="login-form__label" htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              className="login-form__input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div className="login-form__field">
            <label className="login-form__label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="login-form__input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button type="submit" className="login-form__submit">Sign in</button>
        </form>
      </div>
    </div>
  );
}
