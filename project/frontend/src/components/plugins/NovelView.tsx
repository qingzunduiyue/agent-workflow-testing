import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export const NovelView = ({ content }: { content: string }) => (
  <article className="prose prose-slate max-w-none bg-white p-6 rounded-xl shadow-sm w-full">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
  </article>
);
