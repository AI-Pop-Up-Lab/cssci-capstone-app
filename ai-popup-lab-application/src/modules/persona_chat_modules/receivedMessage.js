// component for a received message in the persona chat

import './receivedMessage.css';

function ReceivedMessage({text}) {

  return (
    <div className="ReceivedMessage">
        <div>
          <p className="unbounded-weight300">{text}</p>
          <div id="received-message-bubbletick"></div>
        </div>
    </div>
  );
};

export default ReceivedMessage;