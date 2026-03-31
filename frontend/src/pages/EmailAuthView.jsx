import React, { useMemo } from 'react';
import TwoStepAuthForm from './TwoStepAuthForm';

export default function EmailAuthView({
  agentMessage,
  dataRequired,
  extractedData,
  sessionIdentity,
  isSubmitting,
  onSubmit,
}) {
  const emailInitState = useMemo(() => {
    const extracted = extractedData && typeof extractedData === 'object' ? extractedData : {};
    const session = sessionIdentity && typeof sessionIdentity === 'object' ? sessionIdentity : {};
    const isOtpSent = extracted.is_otp_sent === true || extracted.isOtpSent === true;

    const extractedContact =
      typeof extracted.contact === 'string' && extracted.contact.trim()
        ? extracted.contact.trim()
        : '';
    const sessionContact =
      typeof session.email === 'string' && session.email.trim()
        ? session.email.trim()
        : typeof session.contact === 'string' && session.contact.trim()
          ? session.contact.trim()
          : '';

    return {
      isOtpSent,
      is_otp_sent: isOtpSent,
      contact: extractedContact || sessionContact,
      maskedContact:
        typeof extracted.masked_contact === 'string' && extracted.masked_contact.trim()
          ? extracted.masked_contact.trim()
          : '',
      otpExpirySeconds: extracted.otp_expiry,
      sessionContact,
    };
  }, [extractedData, sessionIdentity]);

  const handleSendOtp = ({ contact }) => {
    return onSubmit('SYSTEM: TRIGGER_OTP_SEND', {
      source: 'email_send_otp',
      contact,
      email: contact,
      mode: 'email',
      hidden: true,
      command: 'TRIGGER_OTP_SEND',
    });
  };

  const handleVerifyOtp = ({ contact, otp }) => {
    return onSubmit(`Email OTP: ${otp}`, {
      source: 'email_verify_otp',
      contact,
      email: contact,
      otp,
      mode: 'email',
    });
  };

  return (
    <TwoStepAuthForm
      mode="email"
      agentMessage={agentMessage}
      dataRequired={dataRequired}
      initialState={emailInitState}
      isSubmitting={isSubmitting}
      onSendOtp={handleSendOtp}
      onVerifyOtp={handleVerifyOtp}
    />
  );
}
