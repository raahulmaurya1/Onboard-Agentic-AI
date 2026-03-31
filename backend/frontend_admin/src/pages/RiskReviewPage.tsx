import React, { useState, useEffect } from 'react';
import { Avatar, Badge, Card, Button, Modal, Alert, Tooltip } from '../components/ui';

// --- Types matching the backend response ---

export interface DocumentInfo {
  document_id: string;
  file_type: string;
  file_url: string;
  status: string;
  content_base64?: string | null;
}

export interface UserInfo {
  id: string;
  phone: string;
  email: string;
  status: string;
  name: string;
  father_name?: string;
  address?: string;
  dob?: string;
  account_type?: string;
  face_verified?: boolean;
  created_at?: string;
  profile_image_base64?: string;
  aadhar_id?: string;
  pan_id?: string;
  verified_data?: Record<string, any>;
  raw_archive?: Record<string, any>;
}

export interface ReviewDataResponse {
  user_info: UserInfo;
  additional_info: Record<string, any> | null;
  documents: DocumentInfo[];
  risk_flags: string[];
  llm_flags: string[];
}

// --- Main Page Component ---

export const RiskReviewPage: React.FC<{ userId: string }> = ({ userId }) => {
  const [data, setData] = useState<ReviewDataResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionSuccess, setActionSuccess] = useState<{ type: 'approve' | 'reject'; message: string } | null>(null);
  
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [modalAction, setModalAction] = useState<'approve' | 'reject' | null>(null);

  useEffect(() => {
    fetchReviewData();
  }, [userId]);

  const fetchReviewData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/risk-review/data?user_id=${userId}`);
      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        setError(errBody.detail || `API error: ${response.status}`);
        setLoading(false);
        return;
      }
      const responseBody = await response.json();
      setData(responseBody);
      setLoading(false);
    } catch (err: any) {
      setError('Network error: could not reach the review API.');
      setLoading(false);
    }
  };

  const handleAction = async (action: 'approve' | 'reject') => {
    setActionLoading(true);
    setActionSuccess(null);
    setError(null);
    try {
      const response = await fetch(`/api/v1/risk-review/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      
      const responseData = await response.json();
      
      if (!response.ok) {
        throw new Error(responseData.detail || responseData.message || `Failed to ${action} application`);
      }
      
      setActionSuccess({ type: action, message: responseData.message || `Application successfully ${action}d.` });
      if (data) {
        setData({...data, user_info: {...data.user_info, status: action === 'approve' ? 'approved' : 'rejected'}});
      }
      setActionLoading(false);
      setModalOpen(false);
    } catch (err: any) {
      setError(err.message || `Failed to ${action} the application.`);
      setActionLoading(false);
      setModalOpen(false);
    }
  };

  const confirmAction = (action: 'approve' | 'reject') => {
    setModalAction(action);
    setModalOpen(true);
  };

  // --- Render ---

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-8 max-w-2xl mx-auto mt-12">
        <Alert color="error" title="Error Loading Data">
          {error}
        </Alert>
        <div className="mt-4">
          <Button onClick={fetchReviewData} size="md">Try Again</Button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { user_info, additional_info, documents, risk_flags, llm_flags } = data;
  const profileSrc = user_info.profile_image_base64 
    ? `data:image/jpeg;base64,${user_info.profile_image_base64}` 
    : undefined;

  const isPendingReview = user_info.status === 'MANUAL_REVIEW' || user_info.status === 'pending_review';

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Application Review</h1>
            <p className="mt-1 text-sm text-gray-500">
              Review applicant details and flagged risks before making a decision.
            </p>
          </div>
          <Badge color={isPendingReview ? 'warning' : 'neutral'}>
            Status: {user_info.status.replace(/_/g, ' ').toUpperCase()}
          </Badge>
        </div>

        {actionSuccess && (
          <Alert color="success" title="Action Completed">
            {actionSuccess.message}
          </Alert>
        )}
        
        {error && data && !actionSuccess && (
          <Alert color="error" title="Action Failed">
            {error}
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* LEFT COLUMN: User Information */}
          <div className="lg:col-span-5 space-y-6">
            <Card className="p-6">
              <div className="flex items-center space-x-4 mb-6">
                <Avatar 
                  src={profileSrc} 
                  fallback={user_info.name ? user_info.name.charAt(0) : 'U'} 
                  size="xl" 
                />
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">{user_info.name || 'Unknown Applicant'}</h2>
                  <p className="text-gray-500 text-sm">{user_info.email}</p>
                </div>
              </div>

              <div className="border-t border-gray-200 py-4">
                <h3 className="text-sm font-medium text-gray-900 mb-3">Personal Details</h3>
                <dl className="grid grid-cols-1 gap-y-3 gap-x-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs text-gray-500">Phone</dt>
                    <dd className="text-sm font-medium text-gray-900">{user_info.phone || 'N/A'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Date of Birth</dt>
                    <dd className="text-sm font-medium text-gray-900">{user_info.dob || 'N/A'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Aadhaar / ID Card</dt>
                    <dd className="text-sm font-medium text-gray-900">{user_info.aadhar_id || 'N/A'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">PAN / Tax ID</dt>
                    <dd className="text-sm font-medium text-gray-900">{user_info.pan_id || 'N/A'}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-xs text-gray-500">Address</dt>
                    <dd className="text-sm font-medium text-gray-900">{user_info.address || 'N/A'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Father's Name</dt>
                    <dd className="text-sm font-medium text-gray-900">{user_info.father_name || 'N/A'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Face Verified</dt>
                    <dd className="text-sm font-medium flex items-center mt-1">
                      {user_info.face_verified ? (
                         <Badge color="success">Yes</Badge>
                      ) : (
                         <Badge color="error">No</Badge>
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Account Type</dt>
                    <dd className="text-sm font-medium text-gray-900 capitalize">{user_info.account_type || 'N/A'}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-xs text-gray-500">User ID</dt>
                    <dd className="text-xs font-mono text-gray-600 break-all">{user_info.id}</dd>
                  </div>
                </dl>
              </div>

              {/* Verified Data */}
              {user_info.verified_data && Object.keys(user_info.verified_data).length > 0 && (
                <div className="border-t border-gray-200 py-4">
                  <h3 className="text-sm font-medium text-gray-900 mb-3">Extracted Verified Data</h3>
                  <div className="bg-gray-100 p-3 rounded-md text-xs font-mono text-gray-800 whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
                    {JSON.stringify(user_info.verified_data, null, 2)}
                  </div>
                </div>
              )}

              {/* Additional Info */}
              {additional_info && Object.keys(additional_info).length > 0 && (
                <div className="border-t border-gray-200 py-4">
                  <h3 className="text-sm font-medium text-gray-900 mb-3">Additional Information</h3>
                  <dl className="grid grid-cols-1 gap-y-3 sm:grid-cols-2">
                    {Object.entries(additional_info).map(([key, value]) => (
                      <div key={key}>
                        <dt className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</dt>
                        <dd className="text-sm font-medium text-gray-900">{String(value)}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}
            </Card>
          </div>

          {/* RIGHT COLUMN: Risk Flags, LLM Review & Documents */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* System Risk Flags Card */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-1">System Risk Flags</h2>
              <p className="text-xs text-gray-500 mb-4">Deterministic flags from Tier 1 &amp; 2 evaluation</p>
              {risk_flags && risk_flags.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {risk_flags.map((flag, index) => {
                    const lowerFlag = flag.toLowerCase();
                    let color: "error" | "warning" | "neutral" = "neutral";
                    if (lowerFlag.includes("fraud") || lowerFlag.includes("aml") || lowerFlag.includes("fail") || lowerFlag.includes("replay") || lowerFlag.includes("bot") || lowerFlag.includes("spoof")) {
                      color = "error";
                    } else if (lowerFlag.includes("mismatch") || lowerFlag.includes("unverified") || lowerFlag.includes("high") || lowerFlag.includes("suspicious")) {
                      color = "warning";
                    }
                    return (
                      <Tooltip key={index} content={flag}>
                        <Badge color={color} size="lg">{flag}</Badge>
                      </Tooltip>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No deterministic risk flags triggered.</p>
              )}
            </Card>

            {/* LLM Review Card (Gemini AML) */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-lg font-semibold text-gray-900">LLM Review</h2>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                  Gemini AML Analysis
                </span>
              </div>
              <p className="text-xs text-gray-500 mb-4">AI-generated findings from Tier 3 cognitive risk evaluation</p>
              {llm_flags && llm_flags.length > 0 ? (
                <div className="space-y-3">
                  {llm_flags.map((flag, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 border border-amber-200"
                    >
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-400 flex items-center justify-center mt-0.5">
                        <span className="text-white text-xs font-bold">{index + 1}</span>
                      </div>
                      <p className="text-sm text-amber-900 leading-relaxed">{flag}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No LLM risk findings detected.</p>
              )}
            </Card>

            {/* Documents Section */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Submitted Media &amp; Documents</h2>
              {documents && documents.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {documents.map((doc) => {
                     const mimeType = doc.file_type || '';
                     const fileUrl = doc.file_url || '';
                     const isImage = mimeType.toLowerCase().includes('image') || /\.(jpeg|jpg|png|gif|webp)$/i.test(fileUrl);
                     const isVideo = mimeType.toLowerCase().includes('video') || /\.(mp4|webm|mov)$/i.test(fileUrl);
                     
                     const dataUriPrefix = isVideo ? (mimeType || 'video/mp4') : (mimeType || 'image/png');
                     const src = doc.content_base64 
                       ? `data:${dataUriPrefix};base64,${doc.content_base64}`
                       : null;

                     return (
                        <div key={doc.document_id} className="border border-gray-200 rounded-lg overflow-hidden flex flex-col group">
                           {/* Media Preview */}
                           <div className="bg-gray-100 aspect-video flex items-center justify-center relative overflow-hidden">
                             {isImage && src ? (
                               <img src={src} alt={fileUrl} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                             ) : isVideo && src ? (
                               <video src={src} controls className="w-full h-full object-contain bg-black" />
                             ) : (
                               <div className="text-center p-4">
                                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                  </svg>
                                  <span className="mt-2 block text-xs font-medium text-gray-900 uppercase">
                                    {mimeType ? mimeType.split('/')[1] : 'FILE'}
                                  </span>
                                  {!src && <p className="text-xs text-gray-400 mt-1">File stored in MinIO</p>}
                               </div>
                             )}
                           </div>
                           {/* Doc Info */}
                           <div className="p-3 bg-white border-t border-gray-200 flex items-center justify-between">
                             <div className="truncate pr-2">
                               <p className="text-sm font-medium text-gray-900 truncate" title={fileUrl}>
                                 {fileUrl.split('/').pop() || 'Unknown File'}
                               </p>
                               <span className="inline-flex mt-1 items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                                 {doc.status}
                               </span>
                             </div>
                             {(!isImage && !isVideo) && src ? (
                               <a href={src} download={fileUrl.split('/').pop()} title="Download File">
                                  <Button size="sm" variant="secondary">Download</Button>
                               </a>
                             ) : (
                               <Button size="sm" variant="secondary">View</Button>
                             )}
                           </div>
                        </div>
                     );
                  })}
                </div>
              ) : (
                <div className="py-8 text-center border-2 border-dashed border-gray-200 rounded-lg">
                   <svg className="mx-auto h-10 w-10 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                   </svg>
                   <p className="text-gray-500 text-sm mt-2">No documents found for this session.</p>
                </div>
              )}
            </Card>

          </div>
        </div>

        {/* Floating Action Bar — visible only if application is still awaiting review */}
        {!actionSuccess && isPendingReview && (
          <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t border-gray-200 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] z-10">
            <div className="max-w-7xl mx-auto flex justify-end items-center space-x-4">
              <span className="text-sm text-gray-500 mr-4">
                Decision for <strong className="text-gray-900">{user_info.name}</strong>
              </span>
              <Button 
                variant="secondary"
                color="error"
                size="lg"
                onClick={() => confirmAction('reject')}
                disabled={actionLoading}
              >
                Reject Application
              </Button>
              <Button 
                variant="primary" 
                size="lg"
                onClick={() => confirmAction('approve')}
                disabled={actionLoading}
              >
                Approve Application
              </Button>
            </div>
          </div>
        )}

      </div>
      
      {/* Spacer for bottom bar */}
      <div className="h-24"></div>

      {/* Confirmation Modal */}
      <Modal 
        isOpen={modalOpen} 
        onClose={() => !actionLoading && setModalOpen(false)}
        title={`Confirm ${modalAction === 'approve' ? 'Approval' : 'Rejection'}`}
      >
        <div className="p-4">
          <p className="text-gray-600 mb-6">
            Are you sure you want to <strong>{modalAction}</strong> the application for <strong>{user_info.name}</strong>? 
            {modalAction === 'reject' && ' This will mark the application as rejected.'}
          </p>
          <div className="flex justify-end space-x-3">
            <Button variant="tertiary" onClick={() => setModalOpen(false)} disabled={actionLoading}>
              Cancel
            </Button>
            <Button 
              variant="primary" 
              color={modalAction === 'reject' ? 'error' : 'primary'}
              onClick={() => modalAction && handleAction(modalAction)}
              isLoading={actionLoading}
            >
              Yes, {modalAction}
            </Button>
          </div>
        </div>
      </Modal>

    </div>
  );
};

export default RiskReviewPage;
