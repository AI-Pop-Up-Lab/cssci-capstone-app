import './awaitingMessage.css';

import Loader from '../loader'

function AwaitingMessage() {

  return (
    <div className="AwaitingMessage">
        <div>
          <Loader />
          <div id="awaiting-message-bubbletick"></div>
        </div>
    </div>
  );
};

export default AwaitingMessage;