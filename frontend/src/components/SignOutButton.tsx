"use client";

export default function SignOutButton() {
  function handleSignOut() {
    sessionStorage.removeItem("authenticated");
    window.location.href = "/";
  }

  return (
    <button type="button" className="sign-out-btn" onClick={handleSignOut}>
      Sign out
    </button>
  );
}
