import { getBrandingConfig } from "@/lib/brandingConfig";
import SignOutButton from "./SignOutButton";

export default function TopBar() {
  const { name, subtitle, logoUrl } = getBrandingConfig();

  return (
    <header className="top-bar">
      {logoUrl ? (
        <img src={logoUrl} alt="University logo" width={36} height={36} className="top-bar__logo" />
      ) : (
        <span data-testid="logo-fallback" className="top-bar__logo-fallback">Logo</span>
      )}
      <div className="top-bar__text">
        <span className="top-bar__name">{name}</span>
        <span className="top-bar__subtitle">{subtitle}</span>
      </div>
      <SignOutButton />
    </header>
  );
}
