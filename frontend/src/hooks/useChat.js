import { useState, useCallback } from 'react';

/**
 * useChat
 * Manages chat message state and bot responses.
 * When you're ready to connect to a real backend, replace
 * the `getBotResponse` function with a fetch() call to your API.
 */

function getBotResponse(userMsg) {
  const msg = userMsg.toLowerCase().trim();

  // Savings / account opening
  if (msg.includes('savings') || msg.includes('account') || msg.includes('open')) {
    return {
      text: "Great choice! Opening a savings account with OnboardAI is quick and easy. Let me collect some basic details.\n\n📋 **To get started, I'll need:**\n• Your full name\n• Mobile number\n• Date of birth\n• PAN card number\n\nCould you please share your **full name** first?",
    };
  }

  // Loan
  if (msg.includes('loan')) {
    return {
      text: "We offer personal loans up to ₹25 lakhs at competitive interest rates starting from 10.5% p.a. 🏦\n\n**Eligibility criteria:**\n• Minimum age: 21 years\n• Minimum income: ₹15,000/month\n• Good credit score (650+)\n\nWould you like to check your eligibility? Please share your **monthly income** to begin.",
    };
  }

  // Eligibility check
  if (msg.includes('eligib')) {
    return {
      text: "I can check your eligibility for various products instantly! 🎯\n\nWhich product are you interested in?\n1. Savings Account\n2. Personal Loan\n3. Credit Card\n4. Fixed Deposit\n\nJust type the number or product name.",
    };
  }

  // Services
  if (msg.includes('service') || msg.includes('learn') || msg.includes('product')) {
    return {
      text: "OnboardAI offers a complete range of banking services:\n\n🏦 **Accounts** — Savings, Current, NRI\n💳 **Cards** — Debit, Credit, Prepaid\n💰 **Loans** — Personal, Home, Auto, Education\n📈 **Investments** — FD, RD, Mutual Funds\n🛡️ **Insurance** — Life, Health, Vehicle\n\nWhich service would you like to explore?",
    };
  }

  // 10-digit mobile number
  if (/^\d{10}$/.test(msg)) {
    return {
      text: `Perfect! I've sent an OTP to ${userMsg.trim()} 📱\n\nPlease enter the **6-digit OTP** you received via SMS.`,
    };
  }

  // OTP
  if (/^\d{4,6}$/.test(msg)) {
    return {
      text: "✅ OTP verified successfully!\n\nYou're almost there! Now I need your **PAN card number** for KYC verification. It looks like: ABCDE1234F",
    };
  }

  // PAN card pattern
  if (/^[A-Za-z]{5}\d{4}[A-Za-z]$/.test(msg)) {
    return {
      text: "Excellent! PAN card verified ✅\n\nLast step — please take a **selfie** or upload a clear photo of your face for biometric KYC. Use the camera button below.\n\nAlmost done! 🎉",
    };
  }

  // Looks like a name (2–3 words)
  if (/^[A-Za-z]+([ ][A-Za-z]+){1,2}$/.test(userMsg.trim()) && userMsg.trim().length > 4) {
    return {
      text: `Thank you, **${userMsg.trim()}**! 😊\n\nNow, could you please share your **10-digit mobile number**? I'll send a quick OTP for verification.`,
    };
  }

  // Default fallback
  return {
    text: "I understand! Let me help you with that. 🌟\n\nTo provide the best assistance, could you tell me more specifically what you're looking for? You can also pick from the quick options below.",
  };
}

export function useChat() {
  const [messages, setMessages] = useState([
    {
      id: 'init',
      role: 'bot',
      text: "Hello! 👋 I'm Luna, your AI banking assistant. I can help you open a new account, apply for loans, or answer any banking questions.\n\nHow can I assist you today?",
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);

  const sendMessage = useCallback((text) => {
    if (!text.trim()) return;

    // Add user message
    const userMsg = {
      id: `user_${Date.now()}`,
      role: 'user',
      text: text.trim(),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    // ─────────────────────────────────────────────────────────────
    // TODO: Replace this block with a real backend fetch when ready
    // Example:
    //   const res = await fetch('https://your-api.com/chat', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ message: text }),
    //   });
    //   const data = await res.json();
    //   const botText = data.reply;
    // ─────────────────────────────────────────────────────────────
    const { text: botText, delay } = getBotResponse(text);

    setTimeout(() => {
      setIsTyping(false);
      const botMsg = {
        id: `bot_${Date.now()}`,
        role: 'bot',
        text: botText,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
    }, delay);
  }, []);

  return { messages, isTyping, sendMessage };
}
