import { newConversation } from "@/app/actions";
export default function Conversations() { return <section className="state"><p className="eyebrow">Conversation workspace</p><h1>Choose a conversation.</h1><p>Reopen one from the list, or start a fresh conversation.</p><form action={newConversation}><button className="primary" type="submit">Start a conversation</button></form></section>; }
