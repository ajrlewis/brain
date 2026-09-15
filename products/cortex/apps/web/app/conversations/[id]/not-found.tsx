import Link from "next/link";
export default function NotFound() { return <section className="state"><h1>Conversation not found.</h1><p>It may not exist, or it may not be available to your account.</p><Link href="/conversations">Return to conversations</Link></section>; }
