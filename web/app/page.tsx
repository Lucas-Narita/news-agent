import { loadDigest } from "@/lib/digest";
import { DigestView } from "@/components/digest/DigestView";

export default function Page() {
  return <DigestView digest={loadDigest()} />;
}
