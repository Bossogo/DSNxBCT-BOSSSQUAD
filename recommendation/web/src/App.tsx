import { useState, useRef, useEffect } from 'react';
import { 
  Send, Sparkles, User, Bot, RotateCcw, 
  Star, ShoppingBag, BookOpen, 
  MapPin, ArrowRight, Loader2, Info
} from 'lucide-react';
import { RecommendationDetailDrawer } from './components/recommendation-detail-drawer';

const API_BASE = 'http://localhost:8001';

interface RecommendationItem {
  rank: number;
  item_name: string;
  platform: string;
  item_category: string;
  avg_rating: number;
  match_reason: string;
  item_id?: string;
  review_count?: number;
  top_keywords?: string[];
  item_metadata?: Record<string, any>;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  recommendations?: RecommendationItem[];
  timestamp: Date;
}

interface DemoProfile {
  name: string;
  description: string;
  id: string;
  platform: string;
  icon: React.ReactNode;
  tags: string[];
}

export default function App() {
  // Session states
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [onboardingComplete, setOnboardingComplete] = useState<boolean>(false);
  const [nigerianContext, setNigerianContext] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentRecommendations, setCurrentRecommendations] = useState<RecommendationItem[]>([]);
  
  // UI states
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState<RecommendationItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Demo user profiles
  const demoProfiles: DemoProfile[] = [
    {
      name: "Audrey",
      description: "Loves moisturizers, face oils, and daily skin health products.",
      id: "AG73BVBKUOH22USSFJA5ZWL7AKXA",
      platform: "amazon",
      icon: <Sparkles className="h-5 w-5 text-indigo-400" />,
      tags: ["Skincare", "Daily Routine", "Hydration"]
    },
    {
      name: "Taylor",
      description: "Focuses on premium hair masks, luxury cosmetics, and eye creams.",
      id: "AEZP6Z2C5AVQDZAJECQYZWQRNG3Q",
      platform: "amazon",
      icon: <ShoppingBag className="h-5 w-5 text-amber-400" />,
      tags: ["Haircare", "Cosmetics", "Anti-Aging"]
    },
    {
      name: "Jordan",
      description: "Values lightweight body creams, subtle fragrances, and budget-friendly packs.",
      id: "AFXF3EGQTQDXMRLDWFU7UBFQZB7Q",
      platform: "amazon",
      icon: <BookOpen className="h-5 w-5 text-emerald-400" />,
      tags: ["Body Creams", "Fragrance", "Value Packs"]
    }
  ];

  // Start recommendation session
  const handleStartSession = async (userId: string | null = null, platform: string | null = null) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetch(`${API_BASE}/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          platform: platform,
          nigerian_context: nigerianContext
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start session. Please make sure the backend server is running.');
      }

      const data = await response.json();
      setSessionId(data.session_id);
      setOnboardingComplete(data.onboarding_complete || false);

      const firstMsg: Message = {
        id: 'first-message',
        role: 'assistant',
        content: data.message,
        recommendations: data.recommendations || [],
        timestamp: new Date()
      };

      setMessages([firstMsg]);
      if (data.recommendations && data.recommendations.length > 0) {
        setCurrentRecommendations(data.recommendations);
      } else {
        setCurrentRecommendations([]);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred while connecting to the backend.');
    } finally {
      setIsLoading(false);
    }
  };

  // Send message to assistant
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || !sessionId || isLoading) return;

    const userMsgText = inputText.trim();
    setInputText('');
    setErrorMessage(null);

    // Append user message immediately
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMsgText,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/session/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMsgText
        })
      });

      if (!response.ok) {
        throw new Error('Lost connection to the recommendations assistant. Please try again.');
      }

      const data = await response.json();
      setOnboardingComplete(data.onboarding_complete);

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.assistant_message,
        recommendations: data.recommendations || [],
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMsg]);
      if (data.recommendations && data.recommendations.length > 0) {
        setCurrentRecommendations(data.recommendations);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not send message.');
    } finally {
      setIsLoading(false);
    }
  };

  // Reset session and return to welcome screen
  const handleResetSession = () => {
    setSessionId(null);
    setMessages([]);
    setCurrentRecommendations([]);
    setOnboardingComplete(false);
    setErrorMessage(null);
  };

  // Open item drawer
  const handleOpenItem = (item: RecommendationItem) => {
    setSelectedItem(item);
    setIsDrawerOpen(true);
  };

  // Helper to format ratings
  const renderStars = (rating: number) => {
    return (
      <div className="flex items-center gap-0.5 text-amber-400">
        <Star className="h-3.5 w-3.5 fill-current" />
        <span className="text-xs font-semibold text-slate-300">{rating.toFixed(1)}</span>
      </div>
    );
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0b0f19] text-slate-100 font-sans">
      
      {/* SIDEBAR */}
      <div className="hidden md:flex w-64 flex-col border-r border-slate-800 bg-[#0f172a]/95">
        {/* Title */}
        <div className="flex items-center gap-2 border-b border-slate-800 p-4">
          <Sparkles className="h-5 w-5 text-indigo-500" />
          <span className="text-sm font-bold tracking-wide uppercase bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            TasteFinder AI
          </span>
        </div>

        {/* Action Button */}
        <div className="p-4">
          <button
            onClick={handleResetSession}
            disabled={!sessionId}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800/40 px-3 py-2 text-xs font-semibold text-slate-200 transition-all hover:bg-slate-800 hover:border-slate-600 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset Session</span>
          </button>
        </div>

        {/* Sidebar Info & Active Recommendations Panel */}
        <div className="flex-1 overflow-y-auto px-4 space-y-4">
          {sessionId && currentRecommendations.length > 0 && (
            <div className="space-y-3">
              <span className="text-2xs font-semibold text-slate-500 uppercase tracking-wider block px-1">
                Top Recommendations
              </span>
              <div className="space-y-2">
                {currentRecommendations.slice(0, 5).map((item) => (
                  <button
                    key={`${item.rank}-${item.item_name}`}
                    onClick={() => handleOpenItem(item)}
                    className="flex w-full items-start gap-2.5 rounded-lg bg-slate-900/40 border border-slate-800/60 p-2 text-left transition-colors hover:bg-slate-800/40 hover:border-slate-700"
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-indigo-500/10 text-3xs font-bold text-indigo-400 border border-indigo-500/20">
                      #{item.rank}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium text-slate-200">{item.item_name}</p>
                      <div className="flex items-center gap-1.5 mt-0.5 text-2xs text-slate-400">
                        <span className="capitalize">{item.platform}</span>
                        <span>•</span>
                        {renderStars(item.avg_rating)}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="border-t border-slate-800 p-4 text-center">
          <div className="flex items-center justify-center gap-1.5 text-2xs text-slate-500">
            <Info className="h-3 w-3" />
            <span>Multi-Platform Recommender</span>
          </div>
        </div>
      </div>

      {/* MAIN CONTAINER */}
      <div className="flex flex-1 flex-col overflow-hidden bg-[#090d16]">
        
        {/* TOP NAVBAR */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-800 px-4 md:px-6 bg-[#090d16]/80 backdrop-blur-xs">
          <div className="flex items-center gap-2">
            <span className="md:hidden text-xs font-bold text-indigo-400 uppercase">TasteFinder</span>
            {sessionId && (
              <span className="hidden md:inline-flex items-center gap-1.5 rounded-full bg-slate-800 px-2 py-0.5 text-2xs font-medium text-slate-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Active Chat</span>
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {nigerianContext && (
              <span className="inline-flex items-center gap-1 rounded-full bg-orange-500/15 border border-orange-500/30 px-2.5 py-0.5 text-2xs font-semibold text-orange-400">
                🇳🇬 Nigerian Warmth Mode
              </span>
            )}
            {sessionId && (
              <button
                onClick={handleResetSession}
                className="md:hidden rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
                title="Reset Session"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            )}
          </div>
        </header>

        {/* ERROR CALLOUT */}
        {errorMessage && (
          <div className="mx-6 mt-4 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-400 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold">Connection Error:</span>
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="font-bold hover:text-rose-200 transition-colors">Dismiss</button>
          </div>
        )}

        {/* CHAT FEED / WELCOME SCREEN */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
          {!sessionId ? (
            
            /* WELCOME PROMPTED START SCREEN */
            <div className="mx-auto max-w-2xl py-8 md:py-12 space-y-8 animate-fade-in">
              <div className="space-y-3 text-center">
                <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 mb-2">
                  <Sparkles className="h-7 w-7" />
                </div>
                <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight leading-none md:text-4xl">
                  Personalized Recommendation Assistant
                </h1>
                <p className="text-sm md:text-base text-slate-400 max-w-lg mx-auto">
                  Find the perfect skincare, haircare, and beauty products across platforms through natural conversation.
                </p>
                <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 px-4 py-1.5 text-2xs text-indigo-300 font-medium mt-2">
                  <Sparkles className="h-3 w-3 shrink-0" />
                  <span>Currently featuring our Beauty &amp; Skincare collection — more categories coming soon!</span>
                </div>
              </div>

              {/* Step 1: Regional Context Select */}
              <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-5 space-y-4">
                <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-1.5">
                  <MapPin className="h-4.5 w-4.5 text-indigo-400" />
                  <span>Choose Conversation Tone & Context</span>
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <button
                    onClick={() => setNigerianContext(false)}
                    className={`flex flex-col items-start text-left p-4 rounded-xl border transition-all ${
                      !nigerianContext 
                        ? 'bg-indigo-600/10 border-indigo-500/60 ring-2 ring-indigo-500/20' 
                        : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <span className="font-bold text-xs text-slate-200">Standard Mode</span>
                    <span className="text-2xs text-slate-400 mt-1 leading-normal">
                      Neutral, direct recommendations matching standard global catalogs.
                    </span>
                  </button>

                  <button
                    onClick={() => setNigerianContext(true)}
                    className={`flex flex-col items-start text-left p-4 rounded-xl border transition-all ${
                      nigerianContext 
                        ? 'bg-orange-500/15 border-orange-500/50 ring-2 ring-orange-500/20' 
                        : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <span className="font-bold text-xs text-orange-400 flex items-center gap-1.5">
                      <span>🇳🇬 Nigerian Warmth Mode</span>
                      <span className="rounded bg-orange-500/20 px-1 py-0.5 text-3xs font-extrabold text-orange-300">BONUS</span>
                    </span>
                    <span className="text-2xs text-slate-400 mt-1 leading-normal">
                      Friendly tone, prioritizes value-for-money, and highlights local equivalence comparisons.
                    </span>
                  </button>
                </div>
              </div>

              {/* Step 2: Choose Startup Method */}
              <div className="space-y-4">
                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider text-center">
                  Select startup option
                </h2>
                
                <div className="grid grid-cols-1 gap-4">
                  {/* Option A: Cold Start Chat Onboarding */}
                  <button
                    onClick={() => handleStartSession(null, null)}
                    disabled={isLoading}
                    className="group relative flex items-center justify-between p-5 rounded-2xl border border-slate-800/80 bg-gradient-to-r from-slate-900/80 to-slate-900/30 hover:border-indigo-500/50 hover:from-indigo-950/20 transition-all text-left disabled:opacity-50"
                  >
                    <div className="space-y-1 pr-4">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-100 group-hover:text-indigo-400 transition-colors">
                          Start Fresh (Chat Onboarding)
                        </span>
                        <span className="rounded bg-indigo-500/10 px-1.5 py-0.5 text-3xs font-semibold text-indigo-400 border border-indigo-500/20">
                          Recommended
                        </span>
                      </div>
                      <p className="text-2xs text-slate-400 leading-normal">
                        Answer 5 quick, simple questions about your budget, interests, and past likes to customize recommendations.
                      </p>
                    </div>
                    {isLoading ? (
                      <Loader2 className="h-5 w-5 text-indigo-400 animate-spin" />
                    ) : (
                      <ArrowRight className="h-5 w-5 text-slate-500 group-hover:translate-x-1 group-hover:text-indigo-400 transition-all" />
                    )}
                  </button>

                  {/* Option B: Load Demo Profiles */}
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-5 space-y-4">
                    <div className="space-y-1">
                      <h3 className="font-bold text-xs text-slate-200">Load a Demo User Profile</h3>
                      <p className="text-2xs text-slate-500 leading-normal">
                        Instantly start a session using real user review history from the catalog. Shows immediate recommendations.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {demoProfiles.map((profile) => (
                        <button
                          key={profile.id}
                          onClick={() => handleStartSession(profile.id, profile.platform)}
                          disabled={isLoading}
                          className="flex flex-col justify-between p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 text-left transition-all hover:bg-slate-800/30 hover:border-slate-700 group disabled:opacity-50"
                        >
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-xs text-slate-200 group-hover:text-indigo-400 transition-colors">
                                {profile.name}
                              </span>
                              {profile.icon}
                            </div>
                            <p className="text-3xs text-slate-400 leading-normal line-clamp-2 h-7">
                              {profile.description}
                            </p>
                          </div>
                          
                          <div className="flex flex-wrap gap-1 mt-3">
                            {profile.tags.map((tag) => (
                              <span key={tag} className="text-4xs rounded bg-slate-800/60 px-1 py-0.25 text-slate-400">
                                {tag}
                              </span>
                            ))}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

          ) : (
            
            /* ACTIVE CHAT FEED */
            <div className="mx-auto max-w-3xl space-y-6">
              {messages.map((message) => {
                const isAssistant = message.role === 'assistant';
                return (
                  <div
                    key={message.id}
                    className={`flex items-start gap-3 md:gap-4 animate-slide-in ${
                      isAssistant ? '' : 'flex-row-reverse'
                    }`}
                  >
                    {/* Avatar */}
                    <div
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-xs font-bold ${
                        isAssistant
                          ? 'bg-indigo-600/10 border-indigo-500/20 text-indigo-400'
                          : 'bg-slate-800 border-slate-700 text-slate-300'
                      }`}
                    >
                      {isAssistant ? <Bot className="h-4.5 w-4.5" /> : <User className="h-4.5 w-4.5" />}
                    </div>

                    {/* Chat Bubble Content */}
                    <div className="space-y-3 max-w-[85%]">
                      <div
                        className={`rounded-2xl px-4 py-3 text-sm leading-relaxed border ${
                          isAssistant
                            ? 'bg-[#151d30]/60 border-slate-800/60 text-slate-200'
                            : 'bg-indigo-600/15 border-indigo-500/20 text-indigo-100'
                        }`}
                      >
                        {/* Format lines nicely */}
                        <div className="space-y-2 whitespace-pre-wrap font-sans">
                          {message.content}
                        </div>
                      </div>

                      {/* HYBRID LAYOUT: Inline Product Recommendations Cards */}
                      {isAssistant && message.recommendations && message.recommendations.length > 0 && (
                        <div className="space-y-2.5 w-full">
                          <span className="text-3xs font-bold text-slate-500 uppercase tracking-widest block px-1">
                            Recommendations
                          </span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {message.recommendations.map((item) => (
                              <button
                                key={`${item.rank}-${item.item_name}`}
                                onClick={() => handleOpenItem(item)}
                                className="flex flex-col justify-between text-left p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/40 hover:bg-slate-800/40 hover:border-slate-700 transition-all group relative overflow-hidden"
                              >
                                <div className="space-y-2 w-full">
                                  <div className="flex items-start justify-between gap-2">
                                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-indigo-500/10 text-3xs font-extrabold text-indigo-400 border border-indigo-500/20">
                                      #{item.rank}
                                    </span>
                                    <span className="capitalize text-4xs rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
                                      {item.platform}
                                    </span>
                                  </div>
                                  <h4 className="font-semibold text-xs text-slate-200 group-hover:text-indigo-400 transition-colors line-clamp-2 h-8 leading-snug">
                                    {item.item_name}
                                  </h4>
                                </div>

                                <div className="flex items-center justify-between border-t border-slate-800/60 pt-2.5 mt-3 w-full">
                                  {renderStars(item.avg_rating)}
                                  <span className="text-3xs text-indigo-400 group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                                    <span>Details</span>
                                    <ArrowRight className="h-2.5 w-2.5" />
                                  </span>
                                </div>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* TYPING LOADER */}
              {isLoading && (
                <div className="flex items-start gap-3 md:gap-4 animate-pulse">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border bg-indigo-600/10 border-indigo-500/20 text-indigo-400">
                    <Bot className="h-4.5 w-4.5" />
                  </div>
                  <div className="rounded-2xl px-4 py-3 bg-[#151d30]/60 border border-slate-800/60 flex items-center gap-1.5 h-9">
                    <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* INPUT PROMPT PANEL */}
        {sessionId && (
          <footer className="border-t border-slate-800 p-4 bg-[#090d16]/80 backdrop-blur-xs">
            <form onSubmit={handleSendMessage} className="mx-auto max-w-3xl flex gap-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                disabled={isLoading}
                placeholder={
                  !onboardingComplete 
                    ? "Type your answer..." 
                    : "Refine (e.g. 'under 20 dollars', 'only budget-friendly skincare')..."
                }
                className="flex-1 rounded-xl border border-slate-800 bg-[#0f172a]/60 px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition-all disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isLoading || !inputText.trim()}
                className="flex items-center justify-center rounded-xl bg-indigo-600 hover:bg-indigo-500 p-2.5 text-white shadow-lg shadow-indigo-600/10 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 active:bg-indigo-700 transition-all disabled:opacity-30 disabled:hover:bg-indigo-600 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="h-4.5 w-4.5 animate-spin" />
                ) : (
                  <Send className="h-4.5 w-4.5" />
                )}
              </button>
            </form>
          </footer>
        )}
      </div>

      {/* DETAIL SLIDE OVER DRAWER */}
      <RecommendationDetailDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        item={selectedItem}
      />
    </div>
  );
}
