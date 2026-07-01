import ReactMarkdown from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

type Props = { markdown: string };

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
