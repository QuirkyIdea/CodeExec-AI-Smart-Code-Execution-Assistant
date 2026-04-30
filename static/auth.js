/**
 * CodeExec AI — Auth Logic (Simple localStorage-based auth)
 */
(function () {
    const API = '';

    // ── DOM refs ──
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    const showSignup = document.getElementById('showSignup');
    const showLogin = document.getElementById('showLogin');
    const loginBtn = document.getElementById('loginBtn');
    const signupBtn = document.getElementById('signupBtn');
    const guestBtn = document.getElementById('guestBtn');
    const authMessage = document.getElementById('authMessage');

    // ── Toggle forms ──
    showSignup?.addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
        hideMessage();
    });
    showLogin?.addEventListener('click', (e) => {
        e.preventDefault();
        signupForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
        hideMessage();
    });

    // ── Password visibility ──
    setupEyeToggle('toggleLoginPw', 'loginPassword');
    setupEyeToggle('toggleSignupPw', 'signupPassword');

    function setupEyeToggle(btnId, inputId) {
        const btn = document.getElementById(btnId);
        const input = document.getElementById(inputId);
        if (!btn || !input) return;
        btn.addEventListener('click', () => {
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            btn.style.color = show ? 'var(--accent-primary)' : '';
        });
    }

    // ── Message helpers ──
    function showMessage(text, type = 'error') {
        authMessage.textContent = text;
        authMessage.className = 'auth-message show ' + type;
    }
    function hideMessage() {
        authMessage.className = 'auth-message';
    }

    // ── Sign Up ──
    signupBtn?.addEventListener('click', async () => {
        const name = document.getElementById('signupName').value.trim();
        const email = document.getElementById('signupEmail').value.trim();
        const password = document.getElementById('signupPassword').value;

        if (!name || !email || !password) {
            return showMessage('Please fill in all fields.');
        }
        if (password.length < 6) {
            return showMessage('Password must be at least 6 characters.');
        }

        signupBtn.disabled = true;
        signupBtn.querySelector('span').textContent = 'Creating...';

        try {
            const res = await fetch(`${API}/api/auth/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                localStorage.setItem('codeexec_user', JSON.stringify(data.user));
                showMessage('Account created! Redirecting...', 'success');
                setTimeout(() => window.location.href = '/home', 800);
            } else {
                showMessage(data.error || 'Signup failed.');
            }
        } catch (err) {
            showMessage('Network error. Please try again.');
        } finally {
            signupBtn.disabled = false;
            signupBtn.querySelector('span').textContent = 'Create Account';
        }
    });

    // ── Sign In ──
    loginBtn?.addEventListener('click', async () => {
        const email = document.getElementById('loginEmail').value.trim();
        const password = document.getElementById('loginPassword').value;

        if (!email || !password) {
            return showMessage('Please fill in all fields.');
        }

        loginBtn.disabled = true;
        loginBtn.querySelector('span').textContent = 'Signing in...';

        try {
            const res = await fetch(`${API}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                localStorage.setItem('codeexec_user', JSON.stringify(data.user));
                showMessage('Welcome back! Redirecting...', 'success');
                setTimeout(() => window.location.href = '/home', 800);
            } else {
                showMessage(data.error || 'Invalid credentials.');
            }
        } catch (err) {
            showMessage('Network error. Please try again.');
        } finally {
            loginBtn.disabled = false;
            loginBtn.querySelector('span').textContent = 'Sign In';
        }
    });

    // ── Guest ──
    guestBtn?.addEventListener('click', () => {
        localStorage.setItem('codeexec_user', JSON.stringify({ name: 'Guest', email: 'guest@codeexec.ai', guest: true }));
        window.location.href = '/home';
    });

    // ── Enter key submits ──
    document.querySelectorAll('.input-wrap input').forEach(input => {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const form = input.closest('.auth-form');
                if (form.id === 'loginForm') loginBtn.click();
                else signupBtn.click();
            }
        });
    });

    // ── Already logged in? Redirect ──
    const existing = localStorage.getItem('codeexec_user');
    if (existing) {
        window.location.href = '/home';
    }
})();
