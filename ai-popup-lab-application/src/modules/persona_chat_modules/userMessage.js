// component for a user message bubble in the persona chat

import './userMessage.css';

function UserMessage({text}) {

  return (
    <div className="UserMessage">
        <div>
          <p className="unbounded-weight300">{text}</p>
          <div id="user-message-bubbletick"></div>
        </div>
    </div>
  );
};

export default UserMessage;