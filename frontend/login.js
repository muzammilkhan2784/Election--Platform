const API_BASE_URL = '/api';

const form = document.getElementById('login-form');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const rememberMeInput = document.getElementById('rememberMe');
const errorEl = document.getElementById('error-message');
const submitBtn = form.querySelector('button[type="submit"]');

function setError(message) {
  errorEl.textContent = message || '';
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  setError('');

  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    setError('Email and password are required.');
    return;
  }

  submitBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        setError('Invalid email or password.');
      } else {
        setError('Unable to sign in. Please try again.');
      }
      return;
    }

    const sessionUser = await response.json();

    // Persist basic session info for the front-end
    if (rememberMeInput.checked) {
      localStorage.setItem('sessionUser', JSON.stringify(sessionUser));
    } else {
      sessionStorage.setItem('sessionUser', JSON.stringify(sessionUser));
    }

    // Redirect to a placeholder dashboard page
    window.location.href = './dashboard.html';
  } catch (err) {
    console.error(err);
    setError('Network error. Check your connection and try again.');
  } finally {
    submitBtn.disabled = false;
  }
});

