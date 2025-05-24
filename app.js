const WS_HOST = '127.0.0.1';
const WS_PORT = 8765;
let socket = null;
let currentUser = null;
let clientId = generateClientId();

let mediaRecorder;
let audioChunks = [];
let recordingStartTime;
let recordingTimer;
let currentAudioBlob = null;
let currentFile = null;

const authButtons = document.getElementById('auth-buttons');
const userInfo = document.getElementById('user-info');
const userAvatar = document.getElementById('user-avatar');
const userName = document.getElementById('user-name');
const logoutBtn = document.getElementById('logout-btn');
const profileBtn = document.getElementById('profile-btn');
const loginBtn = document.getElementById('login-btn');
const registerBtn = document.getElementById('register-btn');
const createNoteBtn = document.getElementById('create-note-btn');
const searchInput = document.getElementById('search-input');
const notesContainer = document.getElementById('notes-container');

const loginModal = document.getElementById('login-modal');
const registerModal = document.getElementById('register-modal');
const noteModal = document.getElementById('note-modal');
const profileModal = document.getElementById('profile-modal');

const closeLoginModal = document.getElementById('close-login-modal');
const closeRegisterModal = document.getElementById('close-register-modal');
const closeNoteModal = document.getElementById('close-note-modal');
const closeProfileModal = document.getElementById('close-profile-modal');

const cancelLogin = document.getElementById('cancel-login');
const cancelRegister = document.getElementById('cancel-register');
const cancelNote = document.getElementById('cancel-note');
const closeProfile = document.getElementById('close-profile');

const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const noteForm = document.getElementById('note-form');

init();

function init() {
    setupEventListeners();
    connectWebSocket();
    checkSavedUser();
}

function checkSavedUser() {
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
        try {
            currentUser = JSON.parse(savedUser);
            updateUIAfterLogin();
            sendInitMessage();
        } catch (e) {
            console.error('Error parsing saved user:', e);
            localStorage.removeItem('currentUser');
        }
    }
}

function setupEventListeners() {
    loginBtn.addEventListener('click', () => showModal(loginModal));
    registerBtn.addEventListener('click', () => showModal(registerModal));
    logoutBtn.addEventListener('click', logout);
    profileBtn.addEventListener('click', showProfile);
    closeProfileModal.addEventListener('click', () => hideModal(profileModal));
    closeProfile.addEventListener('click', () => hideModal(profileModal));

    document.querySelectorAll('input[name="note-type"]').forEach(radio => {
        radio.addEventListener('change', handleNoteTypeChange);
    });

    createNoteBtn.addEventListener('click', () => {
        showCreateNoteModal();
    });

    searchInput.addEventListener('input', debounce(searchNotes, 300));

    closeLoginModal.addEventListener('click', () => hideModal(loginModal));
    closeRegisterModal.addEventListener('click', () => hideModal(registerModal));
    closeNoteModal.addEventListener('click', () => hideModal(noteModal));
    cancelLogin.addEventListener('click', () => hideModal(loginModal));
    cancelRegister.addEventListener('click', () => hideModal(registerModal));
    cancelNote.addEventListener('click', () => hideModal(noteModal));

    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    noteForm.addEventListener('submit', async (e) => {
        await handleNoteSubmit(e);
    });

    document.getElementById('record-btn').addEventListener('click', startRecording);
    document.getElementById('stop-btn').addEventListener('click', stopRecording);
    document.getElementById('play-btn').addEventListener('click', playRecording);

    document.getElementById('file-input').addEventListener('change', handleFileUpload);

    document.getElementById('delete-all-notes').addEventListener('click', deleteAllNotes);

    noteForm.addEventListener('input', () => {
        const title = document.getElementById('note-title').value;
        const noteType = document.querySelector('input[name="note-type"]:checked').value;
        const fileInput = document.getElementById('file-input');
        
        let isValid = title.trim() !== '';
        
        if (noteType === 'image') {
            isValid = isValid && fileInput.files.length > 0;
        } else if (noteType === 'voice') {
            isValid = isValid && currentAudioBlob !== null;
        } else {
            isValid = isValid && document.getElementById('note-content').value.trim() !== '';
        }
        
        document.getElementById('save-note').disabled = !isValid;
    });
}

function handleNoteTypeChange() {
    const noteType = document.querySelector('input[name="note-type"]:checked').value;
    
    document.getElementById('voice-recording-container').style.display = 
        noteType === 'voice' ? 'block' : 'none';
    document.getElementById('file-upload-container').style.display = 
        noteType === 'image' ? 'block' : 'none';
    
    if (noteType !== 'voice') {
        resetRecording();
    }
    if (noteType !== 'image') {
        resetFileUpload();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = () => {
            currentAudioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(currentAudioBlob);
            document.getElementById('audio-preview').src = audioUrl;
            document.getElementById('audio-preview').style.display = 'block';
            document.getElementById('play-btn').disabled = false;
            document.getElementById('recording-status').textContent = 'Recording saved';

            noteForm.dispatchEvent(new Event('input'));
        };
        
        mediaRecorder.start();
        recordingStartTime = Date.now();
        updateRecordingTimer();
        
        document.getElementById('record-btn').disabled = true;
        document.getElementById('stop-btn').disabled = false;
        document.getElementById('recording-status').textContent = 'Recording...';
        document.getElementById('recording-status').style.color = 'var(--danger-color)';
    } catch (error) {
        showAlert('Error accessing microphone: ' + error.message, 'error');
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        clearInterval(recordingTimer);
        
        document.getElementById('record-btn').disabled = false;
        document.getElementById('stop-btn').disabled = true;
    }
}

function playRecording() {
    const audioPreview = document.getElementById('audio-preview');
    audioPreview.play();
}

function updateRecordingTimer() {
    recordingTimer = setInterval(() => {
        const elapsedTime = Math.floor((Date.now() - recordingStartTime) / 1000);
        const minutes = Math.floor(elapsedTime / 60).toString().padStart(2, '0');
        const seconds = (elapsedTime % 60).toString().padStart(2, '0');
        document.getElementById('recording-timer').textContent = `${minutes}:${seconds}`;
    }, 1000);
}

function resetRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    clearInterval(recordingTimer);
    audioChunks = [];
    currentAudioBlob = null;
    
    document.getElementById('audio-preview').src = '';
    document.getElementById('audio-preview').style.display = 'none';
    document.getElementById('record-btn').disabled = false;
    document.getElementById('stop-btn').disabled = true;
    document.getElementById('play-btn').disabled = true;
    document.getElementById('recording-status').textContent = '';
    document.getElementById('recording-timer').textContent = '00:00';
}

function handleFileUpload(event) {
    const files = event.target.files;
    const previewContainer = document.getElementById('file-preview-container');
    
    if (!previewContainer) {
        console.error('File preview container not found');
        return;
    }

    previewContainer.innerHTML = '';
    
    if (files.length === 0) {
        return;
    }

    Array.from(files).forEach((file, index) => {
        const previewElement = document.createElement('div');
        previewElement.className = 'file-preview-item';
        
        if (file.type.startsWith('image/')) {
            const img = document.createElement('img');
            const reader = new FileReader();
            reader.onload = (e) => {
                img.src = e.target.result;
                img.style.maxWidth = '100px';
                img.style.maxHeight = '100px';
            };
            reader.readAsDataURL(file);
            previewElement.appendChild(img);
        } else {
            const icon = document.createElement('i');
            icon.className = 'fas fa-file';
            previewElement.appendChild(icon);
        }
        
        const fileName = document.createElement('span');
        fileName.textContent = file.name;
        previewElement.appendChild(fileName);
        
        const removeBtn = document.createElement('button');
        removeBtn.innerHTML = '&times;';
        removeBtn.className = 'remove-file-btn';
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            removeFile(index);
        };
        previewElement.appendChild(removeBtn);
        
        previewContainer.appendChild(previewElement);
    });
}

function removeFile(index) {
    const fileInput = document.getElementById('file-input');
    const files = Array.from(fileInput.files);
    files.splice(index, 1);
    
    const newFileList = new DataTransfer();
    files.forEach(file => newFileList.items.add(file));
    fileInput.files = newFileList.files;
    
    handleFileUpload({ target: fileInput });
}

function resetFileUpload() {
    document.getElementById('file-input').value = '';
    document.getElementById('image-preview').style.display = 'none';
    document.getElementById('file-download').style.display = 'none';
    currentFile = null;
}

function deleteAllNotes() {
    if (!currentUser) {
        showAlert('You need to login to delete notes', 'error');
        return;
    }

    if (confirm('Are you sure you want to delete ALL your notes? This action cannot be undone!')) {
        const btn = document.getElementById('delete-all-notes');
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
        btn.disabled = true;
        
        sendRequest('delete_all_notes', {
            user_id: currentUser.id
        });
    }
}

function showProfile() {
    if (!currentUser) {
        showAlert('Please login to view profile', 'error');
        return;
    }
    
    document.getElementById('profile-avatar').textContent = currentUser.username.charAt(0).toUpperCase();
    document.getElementById('profile-username').textContent = currentUser.username;
    document.getElementById('profile-email').textContent = currentUser.email;
    document.getElementById('profile-registered').textContent = 'Just now';
    
    showModal(profileModal);
}

function connectWebSocket() {
    try {
        socket = new WebSocket(`ws://${WS_HOST}:${WS_PORT}`);

        socket.addEventListener('open', (event) => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);
            sendInitMessage();
        });

        socket.addEventListener('message', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Received message:', data);
                handleWebSocketMessage(data);
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        });

        socket.addEventListener('close', (event) => {
            console.log('WebSocket disconnected');
            updateConnectionStatus(false);
            setTimeout(connectWebSocket, 3000);
        });

        socket.addEventListener('error', (event) => {
            console.error('WebSocket error:', event);
            updateConnectionStatus(false);
        });
    } catch (e) {
        console.error('WebSocket init error:', e);
        updateConnectionStatus(false);
    }
}

function checkConnection() {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        showAlert('Connection lost. Trying to reconnect...', 'error');
        return false;
    }
    return true;
}

function updateConnectionStatus(connected) {
    if (connected) {
        if (currentUser) {
            loadNotes();
        } else {
            notesContainer.innerHTML = '<p>Connected. Please login to view your notes.</p>';
        }
    } else {
        notesContainer.innerHTML = `
            <div class="connection-error">
                <p>Disconnected from server. Trying to reconnect...</p>
                <div class="spinner"></div>
                <button id="retry-connect">Retry Now</button>
            </div>
        `;
        document.getElementById('retry-connect').addEventListener('click', connectWebSocket);
    }
}

function sendInitMessage() {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    const message = {
        client_id: clientId,
        action: 'init'
    };

    if (currentUser) {
        message.action = 'restore_session';
        message.user_id = currentUser.id;
    }

    socket.send(JSON.stringify(message));
}

async function sendRequest(action, data = {}) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        return { status: 'error', message: 'No connection to server' };
    }

    const request = {
        action,
        request_id: generateRequestId(),
        ...data
    };

    try {
        socket.send(JSON.stringify(request));
        
        return await new Promise((resolve) => {
            const handler = (event) => {
                try {
                    resolve(JSON.parse(event.data));
                } catch (e) {
                    resolve({ status: 'error', message: 'Invalid server response' });
                }
            };
            socket.addEventListener('message', handler, { once: true });
        });
    } catch (error) {
        console.error('Request failed:', error);
        return { 
            status: 'error', 
            message: error.message || 'Request failed' 
        };
    }
}

async function updateNote(noteId, newTitle, newContent) {
    try {
        const response = await sendRequest('update_note', {
            user_id: currentUser.id,
            note_id: noteId,
            update_data: {
                title: newTitle,
                content: newContent,
                time_update: new Date().toISOString()
            }
        });
        console.log('Update response:', response);
        return response;
    } catch (error) {
        console.error('Error updating note:', error);
        return {status: 'error', message: error.message};
    }
}

function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    const submitBtn = loginForm.querySelector('button[type="submit"]');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';
    submitBtn.disabled = true;

    sendRequest('login', {
        email,
        password
    });
}

function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;

    if (password !== confirmPassword) {
        showAlert('Passwords do not match', 'error');
        return;
    }

    const submitBtn = registerForm.querySelector('button[type="submit"]');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';
    submitBtn.disabled = true;

    sendRequest('register', {
        username,
        email,
        password
    });
}

async function handleNoteSubmit(e) {
    e.preventDefault();
    
    if (!currentUser) {
        showAlert('You need to login first', 'error');
        return;
    }

    const noteId = document.getElementById('note-id').value;
    const title = document.getElementById('note-title').value;
    const content = document.getElementById('note-content').value;
    const noteType = document.querySelector('input[name="note-type"]:checked').value;
    const encrypt = document.getElementById('note-encrypt').checked;
    
    const saveBtn = document.getElementById('save-note');
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    saveBtn.disabled = true;

    try {
        let finalContent = content;
        let attachments = [];

        switch(noteType) {
            case 'voice':
                if (currentAudioBlob) {
                    finalContent = "Voice recording";
                    attachments.push({
                        type: 'audio',
                        data: await blobToBase64(currentAudioBlob),
                        name: 'recording.wav'
                    });
                }
                break;
                
            case 'image':
                const fileInput = document.getElementById('file-input');
                if (fileInput.files.length > 0) {
                    finalContent = `${fileInput.files.length} file(s) attached`;
                    for (let i = 0; i < fileInput.files.length; i++) {
                        const file = fileInput.files[i];
                        attachments.push({
                            type: file.type.startsWith('image/') ? 'image' : 'file',
                            name: file.name,
                            data: await fileToBase64(file)
                        });
                    }
                }
                break;
        }

        const requestData = {
            user_id: currentUser.id,
            title: title,
            content: finalContent,
            note_type: noteType,
            encrypt: encrypt
        };

        if (noteId) {
            requestData.note_id = noteId;
        }

        if (attachments.length > 0) {
            requestData.attachments = JSON.stringify(attachments);
        }

        const response = await sendRequest(
            noteId ? 'update_note' : 'create_note',
            requestData
        );

        if (response.status === 'success') {
            showAlert(noteId ? 'Note updated!' : 'Note created!', 'success');
            hideModal(noteModal);
            loadNotes();
        } else {
            showAlert(response.message || 'Error saving note', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error saving note: ' + error.message, 'error');
    } finally {
        saveBtn.innerHTML = noteId ? 'Update' : 'Create';
        saveBtn.disabled = false;
    }
}

function blobToBase64(blob) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result.split(',')[1]);
        reader.readAsDataURL(blob);
    });
}

function fileToBase64(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result.split(',')[1]);
        reader.readAsDataURL(file);
    });
}

function handleWebSocketMessage(data) {
    if (data.action === 'update_note' && data.status === 'success') {
        showAlert('Note updated successfully!', 'success');
        
        const noteElement = document.querySelector(`.note-card[data-id="${data.note._id}"]`);
        if (noteElement) {
            noteElement.querySelector('.note-title').textContent = data.note.title;
            noteElement.querySelector('.note-content').textContent = data.note.content;
            noteElement.querySelector('.note-footer div').textContent = 
                `Updated: ${new Date(data.note.time_update).toLocaleString()}`;
        }
        
        loadNotes();
    }

    switch (data.status) {
        case 'connected':
            console.log('WebSocket connection established');
            if (currentUser) loadNotes();
            break;
            
        case 'success':
            if (data.action === 'login') {
                handleLoginResponse(data);
            } else if (data.action === 'register') {
                handleRegisterResponse(data);
            } else if (data.action === 'get_notes') {
                displayNotes(data.notes);
            } else if (data.action === 'create_note') {
                handleCreateNoteResponse(data);
            } else if (data.action === 'update_note') {
                handleUpdateNoteResponse(data);
            } else if (data.action === 'delete_note') {
                handleDeleteNoteResponse(data);
            } else if (data.action === 'search_notes') {
                displayNotes(data.notes);
            } else if (data.action === 'delete_all_notes') {
                handleDeleteAllNotesResponse(data);
            }
            break;
            
        case 'error':
            showAlert(data.message || 'An error occurred', 'error');
            resetButtons();
            break;
            
        default:
            console.log('Unhandled message:', data);
    }
}

function handleDeleteAllNotesResponse(data) {
    const btn = document.getElementById('delete-all-notes');
    btn.innerHTML = 'Delete All Notes';
    btn.disabled = false;

    if (data.status === 'success') {
        showAlert(data.message, 'success');
        loadNotes();
        hideModal(profileModal);
    } else {
        showAlert(data.message, 'error');
    }
}

function handleLoginResponse(data) {
    const submitBtn = loginForm.querySelector('button[type="submit"]');
    submitBtn.innerHTML = 'Login';
    submitBtn.disabled = false;

    if (data.status === 'success' && data.user) {
        currentUser = data.user;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        
        updateUIAfterLogin();
        hideModal(loginModal);
        loginForm.reset();
        loadNotes();
        showAlert('Login successful!', 'success');
    } else {
        showAlert(data.message || 'Login failed', 'error');
    }
}

function handleRegisterResponse(data) {
    const submitBtn = registerForm.querySelector('button[type="submit"]');
    submitBtn.innerHTML = 'Register';
    submitBtn.disabled = false;

    if (data.status === 'success') {
        hideModal(registerModal);
        registerForm.reset();
        showAlert('Registration successful. Please login.', 'success');
    } else {
        showAlert(data.message || 'Registration failed', 'error');
    }
}

function updateUIAfterLogin() {
    if (!currentUser) return;
    
    authButtons.style.display = 'none';
    userInfo.style.display = 'flex';
    userAvatar.textContent = currentUser.username.charAt(0).toUpperCase();
    userName.textContent = currentUser.username;
    createNoteBtn.style.display = 'block';
    searchInput.disabled = false;
    profileBtn.style.display = 'flex';
}

function updateUIAfterLogout() {
    authButtons.style.display = 'block';
    userInfo.style.display = 'none';
    createNoteBtn.style.display = 'block';
    searchInput.disabled = true;
    profileBtn.style.display = 'none';
}

function logout() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        sendRequest('logout', {
            user_id: currentUser.id
        });
    }
    
    currentUser = null;
    localStorage.removeItem('currentUser');
    updateUIAfterLogout();
    notesContainer.innerHTML = '<p>Disconnected. Please login to view your notes.</p>';
    showAlert('Logged out successfully', 'success');
}

function loadNotes() {
    if (!currentUser) {
        notesContainer.innerHTML = '<p>Please login to view your notes.</p>';
        return;
    }
    
    notesContainer.innerHTML = '<div class="loading"><div class="spinner"></div> Loading notes...</div>';
    sendRequest('get_notes', {
        user_id: currentUser.id
    });
}

function searchNotes() {
    const query = searchInput.value.trim();
    if (!currentUser) {
        showAlert('Please login to search notes', 'error');
        return;
    }

    if (query === '') {
        loadNotes();
        return;
    }

    notesContainer.innerHTML = '<div class="loading"><div class="spinner"></div> Searching...</div>';
    sendRequest('search_notes', {
        user_id: currentUser.id,
        query
    });
}

function showCreateNoteModal() {
    if (!currentUser) {
        showAlert('You need to login first', 'error');
        return;
    }

    document.getElementById('note-modal-title').textContent = 'Create Note';
    document.getElementById('note-id').value = '';
    document.getElementById('note-title').value = '';
    document.getElementById('note-content').value = '';
    document.querySelector('input[name="note-type"][value="text"]').checked = true;
    document.getElementById('note-encrypt').checked = false;
    document.getElementById('save-note').textContent = 'Create';
    
    resetRecording();
    
    resetFileUpload();
    
    showModal(noteModal);
    
    handleNoteTypeChange();
}

function showEditNoteModal(note) {
    document.getElementById('note-modal-title').textContent = 'Edit Note';
    document.getElementById('note-id').value = note._id;
    document.getElementById('note-title').value = note.title;
    document.getElementById('note-content').value = note.content;
    document.querySelector(`input[name="note-type"][value="${note.note_type}"]`).checked = true;
    document.getElementById('note-encrypt').checked = note.is_encrypted || false;
    document.getElementById('save-note').textContent = 'Update';
    
    resetRecording();
    resetFileUpload();
    
    if (note.attachment) {
        try {
            const attachment = typeof note.attachment === 'string' 
                ? JSON.parse(note.attachment) 
                : note.attachment;
            
            if (Array.isArray(attachment)) {
                if (note.note_type === 'voice' && attachment[0]?.type === 'audio') {
                    document.getElementById('audio-preview').src = 
                        `data:audio/wav;base64,${attachment[0].data}`;
                    document.getElementById('audio-preview').style.display = 'block';
                    document.getElementById('play-btn').disabled = false;
                } else if (note.note_type === 'image') {
                    const fileContainer = document.getElementById('file-preview-container');
                    fileContainer.innerHTML = '';
                    
                    attachment.forEach((att, index) => {
                        const previewElement = document.createElement('div');
                        previewElement.className = 'file-preview-item';
                        
                        if (att.type === 'image') {
                            const img = document.createElement('img');
                            img.src = `data:image/*;base64,${att.data}`;
                            img.style.maxWidth = '100px';
                            img.style.maxHeight = '100px';
                            previewElement.appendChild(img);
                        } else {
                            const icon = document.createElement('i');
                            icon.className = 'fas fa-file';
                            previewElement.appendChild(icon);
                        }
                        
                        const fileName = document.createElement('span');
                        fileName.textContent = att.name;
                        previewElement.appendChild(fileName);
                        
                        fileContainer.appendChild(previewElement);
                    });
                }
            } else if (attachment.type) {
                if (note.note_type === 'voice' && attachment.type === 'audio') {
                    document.getElementById('audio-preview').src = 
                        `data:audio/wav;base64,${attachment.data}`;
                    document.getElementById('audio-preview').style.display = 'block';
                    document.getElementById('play-btn').disabled = false;
                } else if (note.note_type === 'image') {
                    const fileContainer = document.getElementById('file-preview-container');
                    fileContainer.innerHTML = '';
                    
                    const previewElement = document.createElement('div');
                    previewElement.className = 'file-preview-item';
                    
                    if (attachment.type === 'image') {
                        const img = document.createElement('img');
                        img.src = `data:image/*;base64,${attachment.data}`;
                        img.style.maxWidth = '100px';
                        img.style.maxHeight = '100px';
                        previewElement.appendChild(img);
                    } else {
                        const icon = document.createElement('i');
                        icon.className = 'fas fa-file';
                        previewElement.appendChild(icon);
                    }
                    
                    const fileName = document.createElement('span');
                    fileName.textContent = attachment.name;
                    previewElement.appendChild(fileName);
                    
                    fileContainer.appendChild(previewElement);
                }
            }
        } catch (e) {
            console.error('Error parsing attachment:', e);
        }
    }
    
    showModal(noteModal);
    
    handleNoteTypeChange();
}

function handleCreateNoteResponse(data) {
    const submitBtn = noteForm.querySelector('button[type="submit"]');
    submitBtn.innerHTML = 'Save';
    submitBtn.disabled = false;

    if (data.status === 'success') {
        hideModal(noteModal);
        if (currentUser) {
            loadNotes();
        }
        showAlert('Note created successfully', 'success');
    } else {
        showAlert(data.message || 'Failed to create note', 'error');
    }
}

function handleUpdateNoteResponse(data) {
    const submitBtn = noteForm.querySelector('button[type="submit"]');
    submitBtn.innerHTML = 'Save';
    submitBtn.disabled = false;

    if (data.status === 'success') {
        hideModal(noteModal);
        loadNotes();
        showAlert('Note updated successfully', 'success');
    } else {
        showAlert(data.message || 'Failed to update note', 'error');
    }
}

function handleDeleteNoteResponse(data) {
    resetButtons();
    
    if (data.status === 'success') {
        loadNotes();
        showAlert('Note deleted successfully', 'success');
    } else {
        showAlert(data.message || 'Failed to delete note', 'error');
    }
}

function resetButtons() {
    document.querySelectorAll('button').forEach(btn => {
        if (btn.innerHTML.includes('fa-spinner')) {
            const originalText = btn.textContent;
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });
}

function displayNotes(notes) {
    notesContainer.innerHTML = '';
    
    if (!notes || !Array.isArray(notes)) {
        notesContainer.innerHTML = '<p>Error loading notes. Please try again.</p>';
        return;
    }

    const userNotes = currentUser ? notes.filter(note => note.user_id === currentUser.id) : [];
    
    if (userNotes.length === 0) {
        notesContainer.innerHTML = currentUser 
            ? '<p>No notes found. Create your first note!</p>'
            : '<p>Please login to view your notes.</p>';
        return;
    }

    userNotes.forEach(note => {
        const noteCard = document.createElement('div');
        noteCard.className = 'note-card';
        noteCard.setAttribute('data-id', note._id);
        
        const createdDate = note.time_creation ? new Date(note.time_creation).toLocaleString() : 'Unknown date';
        const updatedDate = note.time_update ? new Date(note.time_update).toLocaleString() : createdDate;
        
        let content = note.content || '';
        let attachmentHtml = '';
        
        if (note.attachment) {
            try {
                const attachment = typeof note.attachment === 'string' 
                    ? JSON.parse(note.attachment) 
                    : note.attachment;
                
                if (Array.isArray(attachment)) {
                    attachmentHtml = attachment.map(att => {
                        if (att.type === 'audio') {
                            return `
                                <div class="note-attachment">
                                    <audio controls src="data:audio/wav;base64,${att.data}" style="width: 100%"></audio>
                                </div>
                            `;
                        } else if (att.type === 'image') {
                            return `
                                <div class="note-attachment">
                                    <img src="data:image/*;base64,${att.data}" style="max-width: 100%; max-height: 200px;">
                                </div>
                            `;
                        } else {
                            return `
                                <div class="note-attachment">
                                    <a href="data:application/octet-stream;base64,${att.data}" download="${att.name}">
                                        <i class="fas fa-file-download"></i> Download ${att.name}
                                    </a>
                                </div>
                            `;
                        }
                    }).join('');
                } else if (attachment.type) {
                    if (attachment.type === 'audio') {
                        attachmentHtml = `
                            <div class="note-attachment">
                                <audio controls src="data:audio/wav;base64,${attachment.data}" style="width: 100%"></audio>
                            </div>
                        `;
                    } else if (attachment.type === 'image') {
                        attachmentHtml = `
                            <div class="note-attachment">
                                <img src="data:image/*;base64,${attachment.data}" style="max-width: 100%; max-height: 200px;">
                            </div>
                        `;
                    } else {
                        attachmentHtml = `
                            <div class="note-attachment">
                                <a href="data:application/octet-stream;base64,${attachment.data}" download="${attachment.name}">
                                    <i class="fas fa-file-download"></i> Download ${attachment.name}
                                </a>
                            </div>
                        `;
                    }
                }
            } catch (e) {
                console.error('Error parsing attachment:', e);
                attachmentHtml = '<div class="note-attachment">Attachment error</div>';
            }
        }
        
        noteCard.innerHTML = `
            <div class="note-header">
                <div class="note-title">${note.title || 'Untitled'} 
                    ${note.is_encrypted ? '<span class="encrypted-badge">Encrypted</span>' : ''}
                </div>
                <div class="note-type">${note.note_type || 'text'}</div>
            </div>
            <div class="note-content">${content}</div>
            ${attachmentHtml}
            <div class="note-footer">
                <div>Updated: ${updatedDate}</div>
                <div class="note-actions">
                    <button class="edit-btn" data-id="${note._id}">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="delete-btn" data-id="${note._id}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `;
        
        notesContainer.appendChild(noteCard);
    });

    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const noteId = btn.getAttribute('data-id');
            const note = notes.find(n => n._id === noteId);
            if (note) showEditNoteModal(note);
        });
    });

    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!currentUser) {
                showAlert('You need to login to delete notes', 'error');
                return;
            }
            
            const noteId = btn.getAttribute('data-id');
            if (confirm('Are you sure you want to delete this note?')) {
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
                btn.disabled = true;
                sendRequest('delete_note', {
                    user_id: currentUser.id,
                    note_id: noteId
                });
            }
        });
    });
}

function showModal(modal) {
    if (!modal) return;
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function hideModal(modal) {
    if (!modal) return;
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

function showAlert(message, type) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
        ${message}
    `;
    document.body.appendChild(alert);
    
    setTimeout(() => {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
    }, 3000);
}

function generateClientId() {
    return 'client_' + Math.random().toString(36).substr(2, 9);
}

function generateRequestId() {
    return 'req_' + Math.random().toString(36).substr(2, 9);
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            func.apply(this, args);
        }, wait);
    };
}