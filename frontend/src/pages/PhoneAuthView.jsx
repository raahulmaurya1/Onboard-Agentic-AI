import React, { useMemo } from 'react';
import TwoStepAuthForm from './TwoStepAuthForm';

export default function PhoneAuthView({
  agentMessage,
  dataRequired,
  extractedData,
  sessionIdentity,
  isSubmitting,
  onSubmit,
}) {
  const phoneInitState = useMemo(() => {
    const extracted = extractedData && typeof extractedData === 'object' ? extractedData : {};
    const session = sessionIdentity && typeof sessionIdentity === 'object' ? sessionIdentity : {};
    const isOtpSent = extracted.is_otp_sent === true || extracted.isOtpSent === true;

    const extractedContact =
      typeof extracted.contact === 'string' && extracted.contact.trim()
        ? extracted.contact.trim()
        : '';
    const sessionContact =
      typeof session.phone === 'string' && session.phone.trim()
        ? session.phone.trim()
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
      source: 'phone_send_otp',
      contact,
      phone: contact,
      mode: 'phone',
      hidden: true,
      command: 'TRIGGER_OTP_SEND',
    });
  };

  const handleVerifyOtp = ({ contact, otp }) => {
    return onSubmit(`Phone OTP: ${otp}`, {
      source: 'phone_verify_otp',
      contact,
      phone: contact,
      otp,
      mode: 'phone',
    });
  };

  return (
    <TwoStepAuthForm
      mode="phone"
      agentMessage={agentMessage}
      dataRequired={dataRequired}
      initialState={phoneInitState}
      isSubmitting={isSubmitting}
      onSendOtp={handleSendOtp}
      onVerifyOtp={handleVerifyOtp}
    />
  );
}
