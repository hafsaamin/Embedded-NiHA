// src/App.js
import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom'; // Import Router components
import { DndProvider } from 'react-dnd'; // Import DndProvider
import { HTML5Backend } from 'react-dnd-html5-backend'; // Import HTML5 backend
import MainContent from './pages/Chat';
import LoginSignup from './pages/LoginSignup';
import Home from './pages/Home';
// Import FontAwesomeIcon and specific icons you need
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCoffee } from '@fortawesome/free-solid-svg-icons';

function App() {
    return (
        <DndProvider backend={HTML5Backend}> {/* Wrap with DndProvider */}
            <Router>
                <div className="container">
                    <Routes>
                        <Route path="/" element={<Home/>}/>
                        <Route path="/maincontent" element={<MainContent />} />
                        <Route path="/login-signup" element={<LoginSignup />} />
                    </Routes>
                </div>
            </Router>
        </DndProvider>
    );
}

export default App;
