/*
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⠁⠀⠈⠙⠻⣿⣿⠟⠋⠁⠉⠉⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⠀⠀⠀⠀⠀⢠⠟⠁⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿        component of the persona chat, where the user sends and receives
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿        messages from the persona.
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠛⠋⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠉⠙⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿        selected persona data is passed in
⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⠁⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠙⠻⣿⣿⣿⣿⣿⣿⣿⣿          makes calls to backend API which makes calls to LLM for response
⣿⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠀⠀⣿⣷⣦⣤⣄⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣤⣴⣶⣿⡇⠀⠀⠀⠀⠀⠈⠻⣿⣿⣿⣿⣿⣿         
⣿⣿⣿⣿⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠛⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⣹⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠛⠿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠟⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣷⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿          not great code
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣦⣄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⣴⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿          
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠉⠓⠒⠶⠤⠤⢤⣤⣤⣤⣤⣤⣤⣤⣤⣴⣶⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿      will be made better
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⣷⣦⣤⣀⡀⠀⢀⣼⣿⠀⠉⠉⠉⠉⠉⠉⠁⠀⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⢻⣿⣿⣿⡿⢷⣿⡉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿        
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣟⠉⠀⠈⣻⣿⣦⣀⡀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⢿⡁⠹⡈⣳⠶⣿⣿⣽⣛⠋⠁⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⡀⢱⣠⣿⣿⣷⣿⣿⣿⡿⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣶⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
*/


import { useState, useEffect, useRef } from "react";
import { useTranslation, Trans } from "react-i18next";
import axios from "axios";

import './personaChat.css';
import closeCross from '../../assets/images/closeCross.png'
import sendArrow from '../../assets/images/sendArrow.png'

import Loader from "../loader";
import ReceivedMessage from "./receivedMessage";
import UserMessage from "./userMessage";
import AwaitingMessage from "./awaitingMessage";

function PersonaChat({ personaDetails, personaCountry, showChat }) {

  const { t } = useTranslation();

  // below code is for sending and retrieving messages

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [waitingForResponse, setWaitingForResponse] = useState(false);
  const [closeAgreementSection, setCloseAgreementSection] = useState(false);

  const { index, ...personaWithoutIndex } = personaDetails;

  function buildChatHistory(messageList) {
    return messageList
      .filter((message) => message.type === "user" || message.type === "persona")
      .map((message) => ({
        role: message.type === "user" ? "user" : "assistant",
        content: message.text,
      }));
  }

  // function to post message and receive message from backend
  async function sendAndReceiveMessage(persona, country, message, chatHistory) {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/chat/chat_message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          persona_details: persona,
          persona_country: country,
          chat_history: chatHistory
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let currentEvent = "message"
      let firstChunk = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value);
        const blocks = raw.split("\n\n").filter(Boolean);

        for (const block of blocks) {
          const lines = block.split("\n");

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const payload = line.slice(6);
              if (payload === "[DONE]") break;


              const { text } = JSON.parse(payload);

              if (currentEvent === "error") {
                setError(text);
                if (firstChunk) {
                  setMessages(prev => prev.slice(0, -1)); // remove awaiting bubble
                  addMessage("persona", ""); // add empty persona bubble
                  firstChunk = false;
                }
                setMessages(prev => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  updated[updated.length - 1] = { ...last, text };
                  return updated;
                });
              } else {
                if (firstChunk) {
                  setMessages(prev => prev.slice(0, -1)); // remove awaiting bubble
                  addMessage("persona", ""); // add empty persona bubble
                  firstChunk = false;
                }
                setMessages(prev => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  updated[updated.length - 1] = { ...last, text: (last.text || "") + text };
                  return updated;
                });
              }

            currentEvent = "message";
            }
          }
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
    const chatHistory = buildChatHistory(messages);
    setWaitingForResponse(true);
    addMessage("user", message);
    addMessage("awaiting")
    sendAndReceiveMessage(personaDetails, personaCountry, message, chatHistory)
  }


  // below code is for managing and inserting messages in chat

  const [messages, setMessages] = useState([]);
  const numMessages = useRef(0);

  const messageTypes = {
    "user": UserMessage,
    "persona": ReceivedMessage,
    "awaiting": AwaitingMessage
  }

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
              <p>{t('personaPage.chat.warning1')}</p>
              <p>{t('personaPage.chat.warning2')}</p>
              <p>{t('personaPage.chat.warning3')}.</p>
              <p>{t('personaPage.chat.warning4')}</p>
              <p>
                <Trans 
                i18nKey={`personaPage.chat.warning5`} 
                components={{ br: <br/> }} 
                />
              </p>

              <div id="chat-bubble-agree-buttons">
                <div onClick={() => showChat(false)}>{t('personaPage.chat.disagree')}</div>
                <div onClick={() => setCloseAgreementSection(true)}>{t('personaPage.chat.agree')}</div>
              </div>
            </div>}
            </>
            )}

            <div id="persona-chat-header">
                <p id="chat-with-text" className="unbounded-weight300">{t('personaPage.chat.chatWith')}</p>
                <div id="persona-name" className="unbounded-weight400">
                    Persona {index + 1}
                    <div id="anthro-warning">
                        <p className="unbounded-weight400">!</p>
                    </div>
                    <p className="unbounded-weight400" id="chat-not-real-warning">{t('personaPage.chat.notreal')}</p>
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
                  placeholder={t('personaPage.chat.textInputPlaceholder')}
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
