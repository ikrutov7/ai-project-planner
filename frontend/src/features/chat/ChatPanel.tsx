import { useEffect, useRef, useState, type FormEvent } from 'react';
import styles from './ChatPanel.module.css';

export type UiMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
};

type Props = {
  messages: UiMessage[];
  busy: boolean;
  modeHint: string;
  onSend: (text: string) => Promise<void>;
};

const SUGGESTIONS = [
  'Перенеси UX Wireframes на 7 дней позже',
  'Назначь Maya на design',
  'Создай задачу QA Pass на 2 дня',
];

export function ChatPanel({ messages, busy, modeHint, onSend }: Props) {
  const [text, setText] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    setText('');
    await onSend(value);
  };

  return (
    <aside className={styles.panel} aria-label="AI chat">
      <header className={styles.header}>
        <div>
          <h2>AI Chat</h2>
          <p className={styles.hint}>{modeHint}</p>
        </div>
      </header>

      <div className={styles.messages}>
        {messages.map((m) => (
          <div key={m.id} className={`${styles.bubble} ${styles[m.role]}`}>
            {m.content}
          </div>
        ))}
        {busy && <div className={`${styles.bubble} ${styles.assistant}`}>Thinking…</div>}
        <div ref={endRef} />
      </div>

      <div className={styles.suggestions}>
        {SUGGESTIONS.map((s) => (
          <button key={s} type="button" disabled={busy} onClick={() => onSend(s)}>
            {s}
          </button>
        ))}
      </div>

      <form className={styles.form} onSubmit={submit}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Перенеси задачу, смени исполнителя, добавь зависимость…"
          rows={3}
          disabled={busy}
        />
        <button type="submit" disabled={busy || !text.trim()}>
          Send
        </button>
      </form>
    </aside>
  );
}
