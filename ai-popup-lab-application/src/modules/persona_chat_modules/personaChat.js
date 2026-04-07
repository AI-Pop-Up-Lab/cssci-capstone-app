import { useState, useEffect, useRef } from "react";
import axios from "axios";

import './personaChat.css';
import closeCross from '../../assets/images/closeCross.png'
import sendArrow from '../../assets/images/sendArrow.png'

import Loader from "../loader";
import ReceivedMessage from "./receivedMessage";
import UserMessage from "./userMessage";
import AwaitingMessage from "./awaitingMessage";

function PersonaChat({ personaDetails, personaCountry, showChat }) {

  // below code is for sending and retrieving messages

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [waitingForResponse, setWaitingForResponse] = useState(false);
  const [closeAgreementSection, setCloseAgreementSection] = useState(false);

  const { index, ...personaWithoutIndex } = personaDetails;

  // function to post message and receive message from backend
  async function sendAndReceiveMessage(persona, country, message) {
    try {
      const chat_history = gatherChatHistory();

      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/chat/chat_message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          persona_details: persona,
          persona_country: country,
          chat_history: chat_history
        })
      });

      // instead of using awaiting bubble, using an empty persona message
      setMessages(prev => prev.slice(0, -1));
      addMessage("persona", "");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value);
        const lines = raw.split("\n\n").filter(Boolean);

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") break;

          const { text } = JSON.parse(payload);

          // append each chunk to the last message
          setMessages(prev => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            updated[updated.length - 1] = { ...last, text: (last.text || "") + text };
            return updated;
          });
        }
      }

      setError(null);
    } catch (err) {
      setError(err.message);
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setWaitingForResponse(false);
    }
  };

  function sendMessage(message){
    setWaitingForResponse(true);
    addMessage("user", message);
    addMessage("awaiting")
    sendAndReceiveMessage(personaDetails, personaCountry, message)
  }


  // below code is for managing and inserting messages in chat

  const [messages, setMessages] = useState([]);
  const numMessages = useRef(0);

  const messageTypes = {
    "user": UserMessage,
    "persona": ReceivedMessage,
    "awaiting": AwaitingMessage
  }

  function gatherChatHistory(){
    const chatContainer = document.getElementById("persona-chat-history");
    const messageDivs = chatContainer.querySelectorAll(".UserMessage, .ReceivedMessage");

    const history = Array.from(messageDivs).map((div) => ({
      role: div.classList.contains("UserMessage") ? "user" : "assistant",
      content: div.textContent
    }));

    history.pop();

    return history;
  };

  function addMessage(messageType, text=null){

    if(messageType=="awaiting"){
      setMessages(prev => [...prev, {id: 'awaitingTemporary', type: messageType, text: text}])
      return
    }

    setMessages(prev => [...prev, {id: numMessages.current, type: messageType, text: text}])
    numMessages.current += 1;
  }

  // below code is for handling sent messages

  const [inputValue, setInputValue] = useState("");

  function handleSubmit() {
    if (!inputValue.trim()) return; // ignores empty messages
    if (waitingForResponse) return;

    sendMessage(inputValue);

    setInputValue("");
  }

  const chatBottomRef = useRef(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="PersonaChat">
        <div id="chat-bubble">

            {!closeAgreementSection && (

            <>
            {<div id="chat-bubble-agree" className="unbounded-weight300">
              <p>Welcome to the</p>
              <p>AI Pollster Chat</p>
              <p>before you proceed...</p>
              <p>We advise against communicating personal information to the chat.</p>
              <p>Personal data shared in the chat will be stored on Azure Cloud databases, and could be processed by third parties outside of the EU.<br></br>The chats are stored for the purpose of improving the AI system.</p>

              <div id="chat-bubble-agree-buttons">
                <div onClick={() => showChat(false)}>GO BACK</div>
                <div onClick={() => setCloseAgreementSection(true)}>AGREE AND START THE CHAT</div>
              </div>
            </div>}
            </>
            )}

            <div id="persona-chat-header">
                <p id="chat-with-text" className="unbounded-weight300">CHAT WITH</p>
                <div id="persona-name" className="unbounded-weight400">
                    Persona {index + 1}
                    <div id="anthro-warning">
                        <p className="unbounded-weight400">!</p>
                    </div>
                    <p className="unbounded-weight400" id="chat-not-real-warning">NOT A REAL PERSON</p>
                </div>
                <div id="persona-chat-attributes">
                    {Object.entries(personaWithoutIndex).map(([key, value]) => (
                        <p key={key} className="persona-chat-attributes-single unbounded-weight300">#{value}</p>
                    ))}
                </div>
            </div>

            <div id="persona-chat-history">
              {/* {messages.map((message) => (
                message.type === "user"
                  ? <UserMessage key={message.id} text={message.text} />
                  : <ReceivedMessage key={message.id} text={message.text} />
              ))} */}
              {messages.map((message) => {
                const Component = messageTypes[message.type];
                return <Component key={message.id} text={message.text} />;
              })

              }
              <div ref={chatBottomRef} /> {/* reference to scroll to when a new message is sent */}
            </div>

            <div id="persona-chat-input">
                <input 
                  className="unbounded-weight300" 
                  type="text" 
                  alt="Input for persona chat interface" 
                  placeholder="START TYPING HERE..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSubmit();
                  }}
                ></input>
                <div><img onClick={handleSubmit} src={sendArrow} alt="Arrow to send text"></img></div>
            </div>
                
            <div id="chat-close" onClick={() => showChat(false)} src={closeCross} alt="Cross button to close chat window">
              <img id="chat-close-cross" src={closeCross}></img>
            </div>

        </div>
    </div>
  );
};

export default PersonaChat;
