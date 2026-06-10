export default function TopBar() {
  const name =
    process.env.NEXT_PUBLIC_UNIVERSITY_NAME ?? "University AI Operating Center";

  return (
    <header className="top-bar">
      <span className="top-bar__name">{name}</span>
    </header>
  );
}
