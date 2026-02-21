require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const nodemailer = require('nodemailer');
const app = express();
const port = 3001;

const API_BASE = 'http://localhost:8000';

// In-memory session store: token → { user_id, username, email }
const sessions = {};

async function apiPost(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'API error');
    return data;
}

async function apiGet(path) {
    const res = await fetch(`${API_BASE}${path}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'API error');
    return data;
}

app.set('view engine', 'ejs');
app.use(express.static('public'));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

// Attach session user from cookie
app.use((req, res, next) => {
    const token = req.headers.cookie?.match(/session=([^;]+)/)?.[1];
    req.currentUser = token ? sessions[token] : null;
    req.sessionToken = token || null;
    next();
});

function requireAuth(req, res, next) {
    if (!req.currentUser) return res.redirect('/login');
    next();
}

// =====================================================
// EMAIL TRANSPORTER
// =====================================================

const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
        user: process.env.GMAIL_USER,
        pass: process.env.GMAIL_APP_PASSWORD,
    }
});

transporter.verify((error) => {
    if (error) console.log('❌ Email config error:', error.message);
    else console.log('✅ Email server ready');
});

// =====================================================
// AUTH
// =====================================================

app.get('/', (req, res) => res.render('landing', { page: 'landing' }));

app.get('/login', (req, res) => {
    if (req.currentUser) return res.redirect('/home');
    res.render('login', { page: 'login', error: null, mode: 'login' });
});

app.get('/signup', (req, res) => {
    if (req.currentUser) return res.redirect('/home');
    res.render('login', { page: 'login', error: null, mode: 'signup' });
});

app.post('/signup', async (req, res) => {
    const { username, email, password, confirm_password } = req.body;

    if (!username || username.trim().length < 3)
        return res.render('login', { page: 'login', mode: 'signup', error: 'Username must be at least 3 characters.' });
    if (password !== confirm_password)
        return res.render('login', { page: 'login', mode: 'signup', error: 'Passwords do not match.' });

    try {
        const data = await apiPost('/api/auth/signup', { username: username.trim(), email, password });

        // Send verification email
        const verifyLink = `http://localhost:3001/verify/${data.verification_token}`;
        await transporter.sendMail({
            from: `"The Admission Architect" <${process.env.GMAIL_USER}>`,
            to: data.email,
            subject: 'Verify Your Email – The Admission Architect',
            html: `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 30px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #1976D2;">Welcome to The Admission Architect! 🎓</h2>
                <p>Hi <strong>${username.trim()}</strong>, thanks for signing up!</p>
                <p>Please click the button below to verify your email and activate your account.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="${verifyLink}" style="background: #1976D2; color: white; padding: 14px 30px; border-radius: 6px; text-decoration: none; font-size: 16px; font-weight: bold;">Verify My Email</a>
                </div>
                <p style="color:#888; font-size:13px;">If you did not create this account, you can safely ignore this email.</p>
                <p><strong>The Admission Architect Team</strong></p>
            </div>`
        });

        res.render('login', { page: 'login', mode: 'login', error: '✅ Account created! Please check your email to verify your account before logging in.' });
    } catch (err) {
        res.render('login', { page: 'login', mode: 'signup', error: err.message });
    }
});

// Email verification route
app.get('/verify/:token', async (req, res) => {
    try {
        await apiGet(`/api/auth/verify/${req.params.token}`);
        res.render('login', { page: 'login', mode: 'login', error: '✅ Email verified! You can now log in.' });
    } catch (err) {
        res.render('login', { page: 'login', mode: 'login', error: '❌ Invalid or expired verification link.' });
    }
});

app.post('/login', async (req, res) => {
    const { email, password } = req.body;
    if (!email || !password)
        return res.render('login', { page: 'login', mode: 'login', error: 'Email and password are required.' });

    try {
        const data = await apiPost('/api/auth/login', { email, password });
        sessions[data.token] = { user_id: data.user_id, username: data.username, email: data.email };
        res.setHeader('Set-Cookie', `session=${data.token}; Path=/; HttpOnly; Max-Age=${7*24*3600}`);
        res.redirect('/home');
    } catch (err) {
        if (err.message === 'EMAIL_NOT_VERIFIED') {
            return res.render('login', { page: 'login', mode: 'login', error: '⚠️ Please verify your email before logging in. Check your inbox.' });
        }
        res.render('login', { page: 'login', mode: 'login', error: err.message });
    }
});

app.get('/logout', (req, res) => {
    if (req.sessionToken) delete sessions[req.sessionToken];
    res.setHeader('Set-Cookie', 'session=; Path=/; Max-Age=0');
    res.redirect('/login');
});

// =====================================================
// HOME
// =====================================================

app.get('/home', requireAuth, (req, res) => {
    res.render('home', { user: req.currentUser.username, upcoming: null, page: 'home' });
});

// =====================================================
// PROFILE
// =====================================================

app.get('/profile', requireAuth, async (req, res) => {
    const { user_id, username, email } = req.currentUser;
    let history = [], chatHistory = [], profile = { exists: false };

    try {
        const [progressData, chatData, profileData] = await Promise.all([
            apiGet(`/api/progress/${user_id}`),
            apiGet(`/api/chat/history/${user_id}`),
            apiGet(`/api/profile/${user_id}`)
        ]);
        history = progressData.history || [];
        chatHistory = chatData.history || [];
        profile = profileData;
    } catch (e) { /* render with empty data */ }

    res.render('profile', {
        user: { name: username, email, phone: '', photo: '' },
        bookings: [], favorites: [], docs: {},
        history, chatHistory, profile,
        page: 'profile'
    });
});

app.post('/update-profile', requireAuth, (req, res) => {
    const { name, email } = req.body;
    if (name) req.currentUser.username = name;
    if (email) req.currentUser.email = email;
    res.redirect('/profile');
});

app.post('/cancel-booking',  requireAuth, (req, res) => res.redirect('/profile'));
app.post('/remove-favorite', requireAuth, (req, res) => res.redirect('/profile'));
app.post('/upload-doc',      requireAuth, (req, res) => res.redirect('/profile'));

// =====================================================
// UNIVERSITY FINDER
// =====================================================

app.get('/university', requireAuth, (req, res) => {
    res.render('university', { page: 'university', user_id: req.currentUser.user_id });
});

app.post('/api/universities/recommend', requireAuth, async (req, res) => {
    try {
        const { cgpa, major_interest, budget_min, budget_max, preferred_country } = req.body;
        if (cgpa) {
            await apiPost('/api/profile/save', {
                user_id: req.currentUser.user_id,
                cgpa: parseFloat(cgpa),
                major_interest: major_interest || 'Computer Science',
                budget_min: parseFloat(budget_min) || 10000,
                budget_max: parseFloat(budget_max) || 30000,
                preferred_country: preferred_country || 'Any'
            });
        }
        const data = await apiPost('/api/universities/recommend', { user_id: req.currentUser.user_id });
        res.json(data);
    } catch (err) { res.status(400).json({ error: err.message }); }
});

// =====================================================
// TEST MODULES
// =====================================================

app.get('/test-modules', requireAuth, (req, res) => res.render('test-modules', { page: 'test-modules' }));

app.get('/module/:type', requireAuth, (req, res) => {
    const testMap = {
        'listening':  { type: 'listening',  title: "IELTS Listening Practice",   icon: "headphones",    color: "#4CAF50", instructions: "Listen to the AI-generated script, then answer the questions." },
        'reading':    { type: 'reading',    title: "IELTS Reading Practice",     icon: "menu_book",     color: "#FF9800", instructions: "Read the passage carefully and answer the questions." },
        'writing':    { type: 'writing',    title: "IELTS Writing Task 2",       icon: "edit_document", color: "#F44336", instructions: "Write at least 250 words. AI will grade your essay.", passage: "<strong>Prompt:</strong> Some people believe university education should be free for everyone. Others think students should pay. Discuss both views and give your opinion." },
        'speaking':   { type: 'speaking',   title: "IELTS Speaking Practice",    icon: "mic",           color: "#9C27B0", instructions: "Click the mic and speak your answer. AI will transcribe and grade it." },
        'gre-verbal': { type: 'gre-verbal', title: "GRE Verbal Reasoning",       icon: "forum",         color: "#00BFA5", instructions: "Answer the AI-generated verbal reasoning question." },
        'gre-quant':  { type: 'gre-quant',  title: "GRE Quantitative Reasoning", icon: "calculate",     color: "#0288D1", instructions: "Answer the AI-generated quantitative reasoning question." },
    };
    if (!testMap[req.params.type]) return res.redirect('/test-modules');
    res.render('mock-test', { page: 'test-modules', testData: testMap[req.params.type], user_id: req.currentUser.user_id });
});

// API proxy routes
app.post('/api/ielts/reading',        requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/reading',        { user_id: req.currentUser.user_id })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/ielts/listening',      requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/listening',      { user_id: req.currentUser.user_id })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/ielts/grade-writing',  requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/grade-writing',  { user_id: req.currentUser.user_id, essay_text: req.body.essay_text })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/ielts/grade-speaking', requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/grade-speaking', { user_id: req.currentUser.user_id, response_text: req.body.response_text })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/ielts/save-score',     requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/save-score',     { user_id: req.currentUser.user_id, ...req.body })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/gre/question',         requireAuth, async (req, res) => { try { res.json(await apiPost('/api/gre/question',         { user_id: req.currentUser.user_id, topic: req.body.topic })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/gre/submit-answer',    requireAuth, async (req, res) => { try { res.json(await apiPost('/api/gre/submit-answer',    { user_id: req.currentUser.user_id, ...req.body })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/gre/grade-essay',      requireAuth, async (req, res) => { try { res.json(await apiPost('/api/gre/grade-essay',      { user_id: req.currentUser.user_id, essay_text: req.body.essay_text })); } catch(e){ res.status(500).json({error:e.message}); }});

// =====================================================
// AI CHAT
// =====================================================

app.get('/chat', requireAuth, (req, res) => res.render('chat', { page: 'chat' }));

app.post('/api/chat', requireAuth, async (req, res) => {
    try {
        const data = await apiPost('/api/chat', { user_id: req.currentUser.user_id, message: req.body.message });
        res.json(data);
    } catch(e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/progress', requireAuth, async (req, res) => {
    try { res.json(await apiGet(`/api/progress/${req.currentUser.user_id}`)); }
    catch(e) { res.status(500).json({ error: e.message }); }
});

// =====================================================
// HISTORY PAGE
// =====================================================

app.get('/history', requireAuth, async (req, res) => {
    const { user_id } = req.currentUser;
    let testHistory = [], chatHistory = [];
    try {
        const [progressData, chatData] = await Promise.all([
            apiGet(`/api/progress/${user_id}`),
            apiGet(`/api/chat/history/${user_id}`)
        ]);
        testHistory = progressData.history || [];
        chatHistory = chatData.history || [];
    } catch (e) { /* render empty */ }

    res.render('history', { page: 'history', testHistory, chatHistory });
});

// =====================================================
// STATIC PAGES
// =====================================================

app.get('/booking',          requireAuth, (req, res) => res.render('booking',          { page: 'booking' }));
app.get('/voice',            requireAuth, (req, res) => res.render('voice',            { page: 'test-modules' }));
app.get('/settings',         requireAuth, (req, res) => res.render('settings',         { page: 'settings' }));
app.get('/cost-calculator',  requireAuth, (req, res) => res.render('cost-calculator',  { page: 'cost-calculator' }));
app.get('/airport-transfer', requireAuth, (req, res) => res.render('airport-transfer', { page: 'home' }));

app.get('/info/test-prep',           (req, res) => res.render('info-test-prep',           { page: 'info' }));
app.get('/info/living-abroad',       (req, res) => res.render('info-living-abroad',       { page: 'info' }));
app.get('/info/visa-support',        (req, res) => res.render('info-visa',                { page: 'info' }));
app.get('/info/find-university',     (req, res) => res.render('info-find-university',     { page: 'info' }));
app.get('/info/cost-calculator',     (req, res) => res.render('info-cost-calculator',     { page: 'info' }));
app.get('/info/student-essentials',  (req, res) => res.render('info-student-essentials',  { page: 'info' }));
app.get('/info/careers',             (req, res) => res.render('info-careers',             { page: 'info' }));
app.get('/info/virtual-counselling', (req, res) => res.render('info-virtual-counselling', { page: 'info' }));

// =====================================================
// ENQUIRE NOW
// =====================================================

app.post('/enquire', async (req, res) => {
    const { name, email, phone, destination, level } = req.body;
    if (!name || !email) return res.status(400).json({ error: 'Name and email are required.' });

    try {
        await transporter.sendMail({
            from: `"The Admission Architect" <${process.env.GMAIL_USER}>`,
            to: email,
            subject: 'Thank You for Your Enquiry – The Admission Architect',
            html: `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 30px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #1976D2;">Hello, ${name}! 👋</h2>
                <p>Thank you for reaching out to <strong>The Admission Architect</strong>.</p>
                <p>We have received your enquiry about studying in <strong>${destination || 'your preferred destination'}</strong> at <strong>${level || 'your chosen'}</strong> level.</p>
                <p>One of our expert counsellors will get back to you within <strong>24 hours</strong>.</p>
                <hr style="border:none; border-top:1px solid #eee; margin:20px 0;">
                <h3 style="color: #1976D2;">What We Offer:</h3>
                <ul>
                    <li>🎓 University selection &amp; application support</li>
                    <li>📝 IELTS &amp; GRE preparation</li>
                    <li>🌍 Study abroad planning &amp; visa guidance</li>
                    <li>💰 Scholarship &amp; funding advice</li>
                </ul>
                <hr style="border:none; border-top:1px solid #eee; margin:20px 0;">
                <p style="color:#888; font-size:13px;">If you have any urgent queries, feel free to reply to this email.</p>
                <p><strong>The Admission Architect Team</strong></p>
            </div>`
        });
        res.json({ success: true });
    } catch (err) {
        console.error('Email error:', err);
        res.status(500).json({ error: 'Failed to send email.' });
    }
});

app.listen(port, () => {
    console.log(`✅ Frontend running at http://localhost:${port}`);
    console.log(`   Python API must be running at http://localhost:8000`);
});