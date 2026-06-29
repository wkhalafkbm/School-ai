export function getBrandingConfig() {
  return {
    name: process.env.NEXT_PUBLIC_UNIVERSITY_NAME ?? "University AI Operating Center",
    subtitle: process.env.NEXT_PUBLIC_UNIVERSITY_SUBTITLE ?? "Student Journey Intelligence Layer",
    logoUrl: process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL as string | undefined,
  };
}
