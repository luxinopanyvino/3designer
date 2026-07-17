import MessageInput from './MessageInput'
import MessageList from './MessageList'

export default function ChatPanel() {
  return (
    <section className="chat-panel">
      <MessageList />
      <MessageInput />
    </section>
  )
}
