import React from 'react';

export const FinanceView: React.FC<{ response: string }> = ({ response }) => {
  return (
    <div className="finance-secure-view">
      <div className="content">{response}</div>
      {/* 强制底部免责声明 */}
      <footer className="nfa-compliance-warning text-xs text-red-500">
        NFA Disclaimer: 本内容仅供参考，不构成任何投资建议。
      </footer>
    </div>
  );
};
