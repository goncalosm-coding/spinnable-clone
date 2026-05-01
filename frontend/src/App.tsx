import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Workers from "./pages/Workers";
import Chat from "./pages/Chat";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <Routes>
          <Route path="/" element={<Workers />} />
          <Route path="/chat/:workerId" element={<Chat />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}