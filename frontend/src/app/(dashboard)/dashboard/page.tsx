"use client";

import React, { useState, Suspense, useEffect, useRef } from 'react';
import { Skeleton } from "@/components/ui/skeleton";
import { useRouter } from 'next/navigation';
import { Menu } from "lucide-react";
import { ChatInput, ChatInputHandles } from '@/components/thread/chat-input';
import { initiateAgent, createThread, addUserMessage, startAgent, createProject, BillingError } from "@/lib/api";
import { generateThreadName } from "@/lib/actions/threads";
import { useIsMobile } from "@/hooks/use-mobile";
import { useSidebar } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useBillingError } from "@/hooks/useBillingError";
import { BillingErrorAlert } from "@/components/billing/usage-limit-alert";
import { useAccounts } from "@/hooks/use-accounts";
import { isLocalMode, config } from "@/lib/config";
import { toast } from "sonner";

// Constant for localStorage key to ensure consistency
const PENDING_PROMPT_KEY = 'pendingAgentPrompt';

function DashboardContent() {
  const [inputValue, setInputValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [autoSubmit, setAutoSubmit] = useState(false);
  const { billingError, handleBillingError, clearBillingError } = useBillingError();
  const router = useRouter();
  const isMobile = useIsMobile();
  const { setOpenMobile } = useSidebar();
  const { data: accounts } = useAccounts();
  const personalAccount = accounts?.find(account => account.personal_account);
  const chatInputRef = useRef<ChatInputHandles>(null);

  const handleSubmit = async (message: string, options?: { model_name?: string; enable_thinking?: boolean }) => {
    if ((!message.trim() && !(chatInputRef.current?.getPendingFiles().length)) || isSubmitting) return;

    setIsSubmitting(true);

    try {
      const files = chatInputRef.current?.getPendingFiles() || [];
      localStorage.removeItem(PENDING_PROMPT_KEY);

      if (files.length > 0) {
        // Create a FormData instance
        const formData = new FormData();

        // Append the message
        formData.append('message', message);

        // Append all files
        files.forEach(file => {
          formData.append('files', file);
        });

        // Add any additional options
        if (options) {
          formData.append('options', JSON.stringify(options));
        }

        // Call initiateAgent API
        const result = await initiateAgent(formData);
        console.log('Agent initiated with files:', result);

        // Navigate to the thread
        if (result.thread_id) {
          router.push(`/agents/${result.thread_id}`);
        }
      } else {
        // ---- Text-only messages ----
        // 1. Generate a project name
        const projectName = await generateThreadName(message);

        // 2. Create the project
        // Assuming createProject gets the account_id from the logged-in user
        const newProject = await createProject({
          name: projectName,
          description: "", // Or derive a description if desired
        });

        // 3. Create the thread using the new project ID
        const thread = await createThread(newProject.id); // <-- Pass the actual project ID

        // 4. Then add the user message
        await addUserMessage(thread.thread_id, message);

        // 5. Start the agent on this thread with the options
        await startAgent(thread.thread_id, options);

        // 6. Navigate to thread
        router.push(`/agents/${thread.thread_id}`);
      }
    } catch (error: any) {
      console.error('Error during submission process:', error);

      // Check specifically for BillingError (402)
      if (error instanceof BillingError) {
        console.log("Handling BillingError:", error.detail);
        handleBillingError({
          // Pass details from the BillingError instance
          message: error.detail.message || 'Monthly usage limit reached. Please upgrade your plan.',
          currentUsage: error.detail.currentUsage as number | undefined, // Attempt to get usage/limit if backend adds them
          limit: error.detail.limit as number | undefined,
          // Include subscription details if available in the error, otherwise provide defaults
          subscription: error.detail.subscription || {
            price_id: config.SUBSCRIPTION_TIERS.FREE.priceId, // Default to Free tier
            plan_name: "Free"
          }
        });
        // Don't show toast for billing errors, the modal handles it
        setIsSubmitting(false);
        return; // Stop execution
      }
      
      // Handle other types of errors (e.g., network, other API errors)
      // Skip toast in local mode unless it's a connection error
      const isConnectionError = error instanceof TypeError && error.message.includes('Failed to fetch');
      if (!isLocalMode() || isConnectionError) {
         toast.error(error.message || "An unexpected error occurred");
      }
       setIsSubmitting(false); // Reset submitting state on other errors too
    }
    // No finally block needed, state is reset in catch blocks
  };

  // Check for pending prompt in localStorage on mount
  useEffect(() => {
    // Use a small delay to ensure we're fully mounted
    const timer = setTimeout(() => {
      const pendingPrompt = localStorage.getItem(PENDING_PROMPT_KEY);
      
      if (pendingPrompt) {
        setInputValue(pendingPrompt);
        setAutoSubmit(true); // Flag to auto-submit after mounting
      }
    }, 200);
    
    return () => clearTimeout(timer);
  }, []);

  // Auto-submit the form if we have a pending prompt
  useEffect(() => {
    if (autoSubmit && inputValue && !isSubmitting) {
      const timer = setTimeout(() => {
        handleSubmit(inputValue);
        setAutoSubmit(false);
      }, 500);
      
      return () => clearTimeout(timer);
    }
  }, [autoSubmit, inputValue, isSubmitting]);

  return (
    <div className="flex flex-col items-center justify-center h-full w-full">
      {isMobile && (
        <div className="absolute top-4 left-4 z-10">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button 
                variant="ghost" 
                size="icon"
                className="h-8 w-8" 
                onClick={() => setOpenMobile(true)}
              >
                <Menu className="h-4 w-4" />
                <span className="sr-only">Open menu</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Open menu</TooltipContent>
          </Tooltip>
        </div>
      )}

      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[560px] max-w-[90%]">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-medium text-foreground mb-2">Hey </h1>
          <h2 className="text-2xl text-muted-foreground">What would you like Suna to do today?</h2>
        </div>
        
        <ChatInput 
          ref={chatInputRef}
          onSubmit={handleSubmit} 
          loading={isSubmitting}
          placeholder="Describe what you need help with..."
          value={inputValue}
          onChange={setInputValue}
          hideAttachments={false}
        />
      </div>
      
      {/* Billing Error Alert */}
      <BillingErrorAlert
        message={billingError?.message}
        currentUsage={billingError?.currentUsage}
        limit={billingError?.limit}
        accountId={personalAccount?.account_id}
        onDismiss={clearBillingError}
        isOpen={!!billingError}
      />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col items-center justify-center h-full w-full">
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[560px] max-w-[90%]">
          <div className="flex flex-col items-center text-center mb-10">
            <Skeleton className="h-10 w-40 mb-2" />
            <Skeleton className="h-7 w-56" />
          </div>
          
          <Skeleton className="w-full h-[100px] rounded-xl" />
          <div className="flex justify-center mt-3">
            <Skeleton className="h-5 w-16" />
          </div>
        </div>
      </div>
    }>
      <DashboardContent />
    </Suspense>
  );
}
