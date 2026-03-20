require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const nodemailer = require('nodemailer');
const app = express();
const port = 3001;

const API_BASE = 'http://localhost:8000';
const sessions = {};

async function apiPost(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch (e) { throw new Error(`Backend Error: ${text.substring(0, 50)}...`); }
    if (!res.ok) throw new Error(data.detail || data.error || 'API error');
    return data;
}

async function apiGet(path) {
    const res = await fetch(`${API_BASE}${path}`);
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch (e) { throw new Error(`Backend Error: ${text.substring(0, 50)}...`); }
    if (!res.ok) throw new Error(data.detail || data.error || 'API error');
    return data;
}

app.set('view engine', 'ejs');
app.use(express.static('public'));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

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

const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: { user: process.env.GMAIL_USER, pass: process.env.GMAIL_APP_PASSWORD }
});

// --- AUTH ROUTES ---
app.get('/', (req, res) => res.render('landing', { page: 'landing' }));
app.get('/login', (req, res) => { if (req.currentUser) return res.redirect('/home'); res.render('login', { page: 'login', error: null, mode: 'login' }); });
app.get('/signup', (req, res) => { if (req.currentUser) return res.redirect('/home'); res.render('login', { page: 'login', error: null, mode: 'signup' }); });

app.post('/signup', async (req, res) => {
    const { username, email, password, confirm_password } = req.body;
    if (!username || username.trim().length < 3) return res.render('login', { page: 'login', mode: 'signup', error: 'Username must be at least 3 characters.' });
    if (password !== confirm_password) return res.render('login', { page: 'login', mode: 'signup', error: 'Passwords do not match.' });

    try {
        const data = await apiPost('/api/auth/signup', { username: username.trim(), email, password });
        const verifyLink = `http://localhost:3001/verify/${data.verification_token}`;
        await transporter.sendMail({
            from: `"The Admission Architect" <${process.env.GMAIL_USER}>`,
            to: data.email,
            subject: 'Verify Your Email',
            html: `<div style="font-family: Arial, sans-serif; padding: 20px;"><h2>Welcome!</h2><a href="${verifyLink}" style="background: #1976D2; color: white; padding: 10px 20px; text-decoration: none;">Verify My Email</a></div>`
        });
        res.render('login', { page: 'login', mode: 'login', error: '✅ Account created! Check your email to verify before logging in.' });
    } catch (err) { res.render('login', { page: 'login', mode: 'signup', error: err.message }); }
});

app.get('/verify/:token', async (req, res) => {
    try {
        await apiGet(`/api/auth/verify/${req.params.token}`);
        res.render('login', { page: 'login', mode: 'login', error: '✅ Email verified! You can now log in.' });
    } catch (err) { res.render('login', { page: 'login', mode: 'login', error: '❌ Invalid link.' }); }
});

app.post('/login', async (req, res) => {
    try {
        const data = await apiPost('/api/auth/login', { email: req.body.email, password: req.body.password });
        sessions[data.token] = { user_id: data.user_id, username: data.username, email: data.email };
        res.setHeader('Set-Cookie', `session=${data.token}; Path=/; HttpOnly; Max-Age=${7*24*3600}`);
        res.redirect('/home');
    } catch (err) {
        if (err.message === 'EMAIL_NOT_VERIFIED') return res.render('login', { page: 'login', mode: 'login', error: '⚠️ Please verify your email first.' });
        res.render('login', { page: 'login', mode: 'login', error: err.message });
    }
});

app.get('/logout', (req, res) => {
    if (req.sessionToken) delete sessions[req.sessionToken];
    res.setHeader('Set-Cookie', 'session=; Path=/; Max-Age=0');
    res.redirect('/login');
});

// --- MAIN ROUTES ---
app.get('/home', requireAuth, (req, res) => res.render('home', { user: req.currentUser.username, upcoming: null, page: 'home' }));
app.get('/profile', requireAuth, async (req, res) => {
    let history = [], chatHistory = [], profile = { exists: false };
    try {
        const [progressData, chatData, profileData] = await Promise.all([ apiGet(`/api/progress/${req.currentUser.user_id}`), apiGet(`/api/chat/history/${req.currentUser.user_id}`), apiGet(`/api/profile/${req.currentUser.user_id}`) ]);
        history = progressData.history || []; chatHistory = chatData.history || []; profile = profileData;
    } catch (e) {}
    res.render('profile', { user: { name: req.currentUser.username, email: req.currentUser.email, phone: '', photo: '' }, bookings: [], favorites: [], docs: {}, history, chatHistory, profile, page: 'profile' });
});
app.post('/update-profile', requireAuth, (req, res) => res.redirect('/profile'));
app.post('/cancel-booking',  requireAuth, (req, res) => res.redirect('/profile'));
app.post('/remove-favorite', requireAuth, (req, res) => res.redirect('/profile'));
app.post('/upload-doc',      requireAuth, (req, res) => res.redirect('/profile'));

app.get('/university', requireAuth, (req, res) => res.render('university', { page: 'university', user_id: req.currentUser.user_id }));
app.post('/api/universities/recommend', requireAuth, async (req, res) => {
    try {
        if (req.body.cgpa) await apiPost('/api/profile/save', { user_id: req.currentUser.user_id, cgpa: parseFloat(req.body.cgpa), major_interest: req.body.major_interest || 'CS', budget_min: parseFloat(req.body.budget_min)||10000, budget_max: parseFloat(req.body.budget_max)||30000, preferred_country: req.body.preferred_country||'Any' });
        res.json(await apiPost('/api/universities/recommend', { user_id: req.currentUser.user_id }));
    } catch (err) { res.status(400).json({ error: err.message }); }
});

app.get('/test-modules', requireAuth, (req, res) => res.render('test-modules', { page: 'test-modules' }));

// ✅ Randomizing Essay Prompts on Page Load!
app.get('/module/:type', requireAuth, (req, res) => {
    const ieltsWritingPrompts = [
        "<strong>Prompt:</strong> Some people believe university education should be free for everyone. Others think students should pay. Discuss both views and give your opinion.",
        "<strong>Prompt:</strong> In many countries, the proportion of older people is steadily increasing. Does this trend have more positive or negative effects on society?",
        "<strong>Prompt:</strong> With the rise of artificial intelligence, many fear that human jobs will be lost. To what extent do you agree or disagree?"
    ];
    const greAnalyticalPrompts = [
        "<strong>Issue:</strong> 'Governments should place few, if any, restrictions on scientific research and development.' Discuss.",
        "<strong>Issue:</strong> 'To understand the most important characteristics of a society, one must study its major cities.' Discuss.",
        "<strong>Issue:</strong> 'The best way to teach is to praise positive actions and ignore negative ones.' Discuss."
    ];

    const randomIeltsWriting = ieltsWritingPrompts[Math.floor(Math.random() * ieltsWritingPrompts.length)];
    const randomGreAnalytical = greAnalyticalPrompts[Math.floor(Math.random() * greAnalyticalPrompts.length)];

    const testMap = {
        'listening':  { type: 'listening',  title: "IELTS Listening Practice",   icon: "headphones",    color: "#4CAF50", instructions: "Listen to the AI-generated script, then answer the questions." },
        'reading':    { type: 'reading',    title: "IELTS Reading Practice",     icon: "menu_book",     color: "#FF9800", instructions: "Read the passage carefully and answer the questions." },
        'writing':    { type: 'writing',    title: "IELTS Writing Task 2",       icon: "edit_document", color: "#F44336", instructions: "Write at least 250 words. AI will grade your essay.", passage: randomIeltsWriting },
        'speaking':   { type: 'speaking',   title: "IELTS Speaking Practice",    icon: "mic",           color: "#9C27B0", instructions: "Click the mic and speak your answer. AI will transcribe and grade it." },
        'gre-verbal': { type: 'gre-verbal', title: "GRE Verbal Reasoning",       icon: "forum",         color: "#00BFA5", instructions: "Answer the AI-generated verbal reasoning question." },
        'gre-quant':  { type: 'gre-quant',  title: "GRE Quantitative Reasoning", icon: "calculate",     color: "#0288D1", instructions: "Answer the AI-generated quantitative reasoning question." },
        'gre-analytical': { type: 'gre-analytical', title: "GRE Analytical Writing", icon: "edit_document", color: "#00897B", instructions: "Write an essay analysing the given issue. AI will grade it on a 0–6 scale.", passage: randomGreAnalytical },
    };
    if (!testMap[req.params.type]) return res.redirect('/test-modules');
    res.render('mock-test', { page: 'test-modules', testData: testMap[req.params.type], user_id: req.currentUser.user_id });
});

app.post('/api/ielts/reading',        requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/reading',        { user_id: req.currentUser.user_id })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/ielts/listening',      requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/listening',      { user_id: req.currentUser.user_id })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/ielts/grade-writing',  requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/grade-writing',  { user_id: req.currentUser.user_id, essay_text: req.body.essay_text })); } catch(e){ res.status(500).json({error:e.message}); }});
// ✅ Sending the topic over to the API
app.post('/api/ielts/grade-speaking', requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/grade-speaking', { user_id: req.currentUser.user_id, response_text: req.body.response_text, topic: req.body.topic })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/ielts/save-score',     requireAuth, async (req, res) => { try { res.json(await apiPost('/api/ielts/save-score',     { user_id: req.currentUser.user_id, ...req.body })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/gre/question',         requireAuth, async (req, res) => { try { res.json(await apiPost('/api/gre/question',         { user_id: req.currentUser.user_id, topic: req.body.topic })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/gre/submit-answer',    requireAuth, async (req, res) => { try { res.json(await apiPost('/api/gre/submit-answer',    { user_id: req.currentUser.user_id, ...req.body })); } catch(e){ res.status(500).json({error:e.message}); }});
app.post('/api/gre/grade-essay',      requireAuth, async (req, res) => { try { res.json(await apiPost('/api/gre/grade-essay',      { user_id: req.currentUser.user_id, essay_text: req.body.essay_text })); } catch(e){ res.status(500).json({error:e.message}); }});

app.get('/chat', requireAuth, (req, res) => res.render('chat', { page: 'chat' }));
app.post('/api/chat', requireAuth, async (req, res) => { try { res.json(await apiPost('/api/chat', { user_id: req.currentUser.user_id, message: req.body.message, bot_type: req.body.bot_type || 'general' })); } catch(e) { res.status(500).json({ error: e.message }); }});
app.get('/api/progress', requireAuth, async (req, res) => { try { res.json(await apiGet(`/api/progress/${req.currentUser.user_id}`)); } catch(e) { res.status(500).json({ error: e.message }); }});

app.get('/history', requireAuth, async (req, res) => {
    let testHistory = [], chatHistory = [];
    try {
        const [progressData, chatData] = await Promise.all([ apiGet(`/api/progress/${req.currentUser.user_id}`), apiGet(`/api/chat/history/${req.currentUser.user_id}`) ]);
        testHistory = progressData.history || []; chatHistory = chatData.history || [];
    } catch (e) {}
    res.render('history', { page: 'history', testHistory, chatHistory });
});

// --- STATIC FILES ---
app.get('/booking',          requireAuth, (req, res) => res.render('booking',          { page: 'booking' }));
app.get('/voice',            requireAuth, (req, res) => res.render('voice',            { page: 'test-modules' }));
app.get('/settings',         requireAuth, (req, res) => res.render('settings',         { page: 'settings' }));
app.get('/cost-calculator',  requireAuth, (req, res) => res.render('cost-calculator',  { page: 'cost-calculator' }));
app.get('/airport-transfer', requireAuth, (req, res) => res.render('airport-transfer', { page: 'home' }));
app.get('/support-bot',                   (req, res) => res.render('support-bot',      { page: 'support-bot' }));
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
            subject: 'We have received your enquiry – The Admission Architect',
            html: `
            <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: auto; padding: 30px; border: 1px solid #eaeaea; border-radius: 10px; background-color: #ffffff;">
                
                <div style="text-align: center; margin-bottom: 25px;">
                    <h2 style="color: #1976D2; margin: 0;">The Admission Architect</h2>
                </div>
                
                <p style="color: #333; font-size: 16px;">Dear <strong>${name}</strong>,</p>
                
                <p style="color: #555; font-size: 15px; line-height: 1.6;">
                    Thank you for reaching out to us. We have successfully received your information and are thrilled to help you begin your study abroad journey.
                </p>
                
                <div style="background-color: #f9fafb; border-left: 4px solid #1976D2; padding: 15px 20px; margin: 25px 0; border-radius: 4px;">
                    <h3 style="margin-top: 0; color: #333; font-size: 16px;">Your Enquiry Details:</h3>
                    <ul style="list-style: none; padding: 0; margin: 0; color: #555; font-size: 15px; line-height: 1.8;">
                        <li><strong>Phone Number:</strong> ${phone || 'Not provided'}</li>
                        <li><strong>Preferred Destination:</strong> ${destination || 'Not specified'}</li>
                        <li><strong>Study Level:</strong> ${level || 'Not specified'}</li>
                    </ul>
                </div>
                
                <p style="color: #555; font-size: 15px; line-height: 1.6;">
                    One of our expert educational consultants is currently reviewing your profile and will get in touch with you shortly at the phone number provided to discuss your next steps.
                </p>
                
                <p style="color: #555; font-size: 15px; line-height: 1.6;">
                    If you have any immediate questions, feel free to reply directly to this email.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eaeaea; margin: 30px 0;">
                
                <p style="color: #888; font-size: 13px; text-align: center; margin: 0;">
                    Warm regards,<br>
                    <strong>The Admission Architect Team</strong>
                </p>
                
            </div>`
        });
        res.json({ success: true });
    } catch (err) {
        console.error('Email error:', err);
        res.status(500).json({ error: 'Failed to send email.' });
    }
});

app.get('/privacy-policy', (req, res) => { res.render('info-privacy', { page: 'legal' }); });
app.get('/terms-of-service', (req, res) => { res.render('info-terms', { page: 'legal' }); });

app.listen(port, () => console.log(`✅ Frontend running at http://localhost:${port}`));
module.exports = app; // ✅ Required for Vercel Serverless deployment