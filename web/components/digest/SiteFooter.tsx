const REPO_URL = "https://github.com/Lucas-Narita/news-agent";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t-2 border-ink/15 pt-8 lg:mt-24">
      <div className="flex flex-col gap-3 text-sm text-ink/70 sm:flex-row sm:items-center sm:justify-between">
        <p>
          Built by Lucas Narita ·{" "}
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="font-bold text-ink hover:underline"
          >
            source on GitHub
          </a>
        </p>
        <p>Python agents · Claude · Next.js · rebuilt daily at 04:00 UTC</p>
      </div>
    </footer>
  );
}
