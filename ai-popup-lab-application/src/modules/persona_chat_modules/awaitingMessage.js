// component to display a placeholder animation 'message' to indicate the website is awaiting a response from the backend

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