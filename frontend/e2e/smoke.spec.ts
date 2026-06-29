import { test, expect } from "@playwright/test";

const BANNED_TERMS = ["watsonx", "ibm", "presenter", "demo", "reset"];

// AuthGuard reads sessionStorage on mount. Inject the flag via addInitScript
// so it's present before the first navigation — no extra page load required.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("authenticated", "true"));
});

// Visible text check: scan all text nodes in the page body
async function assertNoBannedTerms(page: import("@playwright/test").Page) {
  const bodyText = await page.locator("body").innerText();
  const lower = bodyText.toLowerCase();
  for (const term of BANNED_TERMS) {
    expect(lower, `Page should not contain "${term}"`).not.toContain(term);
  }
}

// ---------------------------------------------------------------------------
// Cycle 1 — tracer bullet: Overview page renders
// ---------------------------------------------------------------------------

test("Overview page renders", async ({ page }) => {
  await page.goto("/");
  await expect(page).not.toHaveURL(/error/);
  await expect(page.locator("body")).toBeVisible();
});

// ---------------------------------------------------------------------------
// Cycle 2 — all eight nav links render their pages (no crash)
// ---------------------------------------------------------------------------

const PAGES = [
  { label: "Overview", path: "/" },
  { label: "Admissions", path: "/admissions" },
  { label: "Enrollment", path: "/enrollment" },
  { label: "Teaching Readiness", path: "/teaching-readiness" },
  { label: "Academic Risk", path: "/academic-risk" },
  { label: "Progression", path: "/progression" },
  { label: "Career & Alumni", path: "/career-alumni" },
  { label: "Workflow Activity", path: "/workflow-activity" },
];

for (const { label, path } of PAGES) {
  test(`${label} page renders without error`, async ({ page }) => {
    await page.goto(path);
    // Next.js error pages include an "Application error" heading
    await expect(page.getByRole("heading", { name: /application error/i })).not.toBeVisible();
    await expect(page.locator("main")).toBeVisible();
  });
}

// ---------------------------------------------------------------------------
// Cycle 3 — nav sidebar is present on every page
// ---------------------------------------------------------------------------

test("Sidebar nav is present on all pages", async ({ page }) => {
  for (const { path } of PAGES) {
    await page.goto(path);
    await expect(page.getByRole("navigation", { name: /journey stages/i })).toBeVisible();
  }
});

// ---------------------------------------------------------------------------
// Cycle 4 — primary action buttons are present on stage pages
// ---------------------------------------------------------------------------

test("Admissions page has Recommend Pathway button", async ({ page }) => {
  await page.goto("/admissions");
  await expect(page.getByRole("button", { name: "Recommend Pathway" })).toBeVisible();
});

test("Enrollment page has Validate Schedule button", async ({ page }) => {
  await page.goto("/enrollment");
  await expect(page.getByTestId("validate-schedule-btn")).toBeVisible();
});

test("Teaching Readiness page has Prepare Cohort Brief button", async ({ page }) => {
  await page.goto("/teaching-readiness");
  await expect(page.getByTestId("prepare-cohort-brief-btn")).toBeVisible();
});

test("Academic Risk page has Approve Intervention button", async ({ page }) => {
  await page.goto("/academic-risk");
  await expect(page.getByTestId("approve-intervention-btn")).toBeVisible();
});

test("Progression page has Update Graduation Plan button", async ({ page }) => {
  await page.goto("/progression");
  await expect(page.getByRole("button", { name: "Update Graduation Plan" })).toBeVisible();
});

test("Career & Alumni page has Recommend Career Path button", async ({ page }) => {
  await page.goto("/career-alumni");
  await expect(page.getByRole("button", { name: "Recommend Career Path" })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Cycle 5 — each primary action triggers an approval modal
// ---------------------------------------------------------------------------

test("Admissions action button triggers approval modal", async ({ page }) => {
  await page.goto("/admissions");
  await page.getByRole("button", { name: "Recommend Pathway" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("Enrollment action button triggers approval modal", async ({ page }) => {
  await page.goto("/enrollment");
  await page.getByTestId("validate-schedule-btn").click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("Teaching Readiness action button triggers approval modal", async ({ page }) => {
  await page.goto("/teaching-readiness");
  await page.getByTestId("prepare-cohort-brief-btn").click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("Academic Risk action button triggers approval modal", async ({ page }) => {
  await page.goto("/academic-risk");
  await page.getByTestId("approve-intervention-btn").click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("Progression action button triggers approval modal", async ({ page }) => {
  await page.goto("/progression");
  await page.getByRole("button", { name: "Update Graduation Plan" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("Career & Alumni action button triggers approval modal", async ({ page }) => {
  await page.goto("/career-alumni");
  await page.getByRole("button", { name: "Recommend Career Path" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

// ---------------------------------------------------------------------------
// Cycle 6 — no banned branding terms visible on any page
// ---------------------------------------------------------------------------

for (const { label, path } of PAGES) {
  test(`${label} page shows no banned branding terms`, async ({ page }) => {
    await page.goto(path);
    await assertNoBannedTerms(page);
  });
}
