import { describe, it, expect, afterEach } from "vitest";
import { getBrandingConfig } from "./brandingConfig";

afterEach(() => {
  delete process.env.NEXT_PUBLIC_UNIVERSITY_NAME;
  delete process.env.NEXT_PUBLIC_UNIVERSITY_SUBTITLE;
  delete process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL;
});

describe("getBrandingConfig", () => {
  it("returns default name when env var is absent", () => {
    expect(getBrandingConfig().name).toBe("University AI Operating Center");
  });

  it("returns name from NEXT_PUBLIC_UNIVERSITY_NAME", () => {
    process.env.NEXT_PUBLIC_UNIVERSITY_NAME = "King Salman University";
    expect(getBrandingConfig().name).toBe("King Salman University");
  });

  it("returns default subtitle when env var is absent", () => {
    expect(getBrandingConfig().subtitle).toBe("Student Journey Intelligence Layer");
  });

  it("returns subtitle from NEXT_PUBLIC_UNIVERSITY_SUBTITLE", () => {
    process.env.NEXT_PUBLIC_UNIVERSITY_SUBTITLE = "Intelligent Student Services";
    expect(getBrandingConfig().subtitle).toBe("Intelligent Student Services");
  });

  it("returns undefined logoUrl when env var is absent", () => {
    expect(getBrandingConfig().logoUrl).toBeUndefined();
  });

  it("returns logoUrl from NEXT_PUBLIC_UNIVERSITY_LOGO_URL", () => {
    process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL = "https://example.com/logo.png";
    expect(getBrandingConfig().logoUrl).toBe("https://example.com/logo.png");
  });
});
