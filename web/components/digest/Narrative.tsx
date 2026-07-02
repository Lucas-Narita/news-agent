import ReactMarkdown from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

type Props = { markdown: string };

// Demote h1/h2 so the page keeps a single <h1>. Typography is applied by the parent
// via Tailwind arbitrary variants (see DigestHero) so it recompiles reliably.
export function Narrative({ markdown }: Props) {
  return (
    <ReactMarkdown
      rehypePlugins={[[rehypeSanitize, defaultSchema]]}
      components={{ h1: "h2", h2: "h3" }}
    >
      {markdown}
    </ReactMarkdown>
  );
}
