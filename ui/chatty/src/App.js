import logo from './logo.svg';
import './App.css';
import ChatBot from 'react-chatbotify';
import { useState } from 'react';
function App() {
  const [message, setMessage] = useState("")
  const [messageLog, setMessageLog] = useState([]);
  const [convStr, setConv] = useState("")

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessageLog([...messageLog, { role: "user", content: message }]);
    setConv("");
    const response = await fetch(
      "http://localhost:8000/stream",
      {
        method: "POST",
        headers: {"Content-Type": 'application/json', "accept": 'application/json'},
        body: JSON.stringify({"content": message})
      }
    );
    const reader = response.body?.pipeThrough(new TextDecoderStream()).getReader()
    while (true) {
      const {value, done} = await reader.read()
      if (done) break
      setMessageLog((prev) => [...prev, {role: "assistant", content: value}]);
      setConv((prev) => [prev, value].join())
    }
  }

  const submitChat = async (params) => {
    // setMessageLog([...messageLog, { role: "user", content: params.userInput }]);
    const response = await fetch(
      "http://localhost:8000/stream",
      {
        method: "POST",
        headers: {"Content-Type": 'application/json', "accept": 'application/json'},
        body: JSON.stringify({"content": params.userInput})
      }
    );
    const reader = response.body?.pipeThrough(new TextDecoderStream()).getReader()
    let text = "";
    let offset = 0;
    let result = await reader.read()
    // while (true) {
    while (true) {
      // const {value, done} = reader.read()
      // if (done) break
        text += result.value;
        for (let i = offset; i < result.value.length; i ++) {
          await params.streamMessage(text.slice(0, i + 1));
          await new Promise(resolve => setTimeout(resolve, 50));
        }
        offset += result.value.length;
        result = await reader.read();
        if (result.done) {
          text += result.value;
          break
        }
        // const {value, done} = reader.read()
    }

    // in case any remaining chunks are missed (e.g. timeout)
    // you may do your own nicer logic handling for large chunks
    for (let i = offset; i < text.length; i++) {
      await params.streamMessage(text.slice(0, i + 1));
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    // await params.streamMessage(text);
    if (result?.value) {
      await params.streamMessage(result.value);
    }

    await params.endStreamMessage();
  }

	const flow={
		start: {
			message: "Hello how can I help you today?",
			path: "llm_graph"
		},
		llm_graph: {
			message: async (params) => {
				await submitChat(params);
			},
			path: () => {
				return "llm_graph"
			}
		}
	}
  return (
    <>
      <ChatBot flow={flow} settings={{chatHistory: {storageKey: "example_real_time_stream"}}}  />
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <p>
            Edit <code>src/App.js</code> and save to reload.
          </p>
          <a
            className="App-link"
            href="https://reactjs.org"
            target="_blank"
            rel="noopener noreferrer"
          >
            Learn React
          </a>
        </header>
      </div>
    </>
  );
}

export default App;
