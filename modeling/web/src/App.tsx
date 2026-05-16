import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Star,
  User,
  Globe,
  AlertCircle,
  ArrowRight,
  Search,
  ShoppingBag,
  Utensils,
  BookOpen,
  CheckCircle2,
  RefreshCw,
  Info,
} from "lucide-react";

const API_BASE = "http://localhost:8000";

interface RetrievedReview {
  item_name: string;
  item_category: string;
  review_text: string;
  rating: number;
  platform: string;
  item_metadata?: Record<string, any>;
}

interface UserProfile {
  mean_rating: number;
  std_rating: number;
  typical_review_length: string;
  common_themes: string[];
  total_reviews: number;
}

interface SimulateResponse {
  composite_user_id: string;
  simulated_review: string;
  predicted_rating: number;
  confidence: string;
  retrieved_reviews_used: RetrievedReview[];
  user_profile: UserProfile;
}

interface UserSelectorItem {
  composite_user_id: string;
  review_count: number;
}

export default function App() {
  // Navigation / Loading States
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("");
  const [users, setUsers] = useState<UserSelectorItem[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loadingUsers, setLoadingUsers] = useState<boolean>(false);
  const [loadingSimulation, setLoadingSimulation] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string>("");

  // Form Fields
  const [itemName, setItemName] = useState<string>("");
  const [itemCategory, setItemCategory] = useState<string>("");
  const [itemLocation, setItemLocation] = useState<string>("");
  const [itemPrice, setItemPrice] = useState<string>("Moderate");
  const [itemDescription, setItemDescription] = useState<string>("");
  const [nigerianContext, setNigerianContext] = useState<boolean>(false);

  // Simulation Results
  const [simulationResult, setSimulationResult] =
    useState<SimulateResponse | null>(null);
  const [textEffectIndex, setTextEffectIndex] = useState<number>(0);
  const [typewriterText, setTypewriterText] = useState<string>("");

  // Initial platforms fetch
  useEffect(() => {
    fetchPlatforms();
  }, []);

  // Fetch users when platform changes
  useEffect(() => {
    if (selectedPlatform) {
      fetchUsers(selectedPlatform);
    }
  }, [selectedPlatform]);

  // Typewriter effect for simulated reviews
  useEffect(() => {
    if (simulationResult?.simulated_review) {
      setTypewriterText("");
      setTextEffectIndex(0);
    }
  }, [simulationResult]);

  useEffect(() => {
    if (
      simulationResult?.simulated_review &&
      textEffectIndex < simulationResult.simulated_review.length
    ) {
      const timer = setTimeout(() => {
        setTypewriterText(
          (prev) => prev + simulationResult.simulated_review[textEffectIndex],
        );
        setTextEffectIndex((prev) => prev + 1);
      }, 5); // Fast typing speed
      return () => clearTimeout(timer);
    }
  }, [simulationResult, textEffectIndex]);

  const fetchPlatforms = async () => {
    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/platforms`);
      if (!res.ok) throw new Error("Could not fetch platforms");
      const data = await res.json();
      const platformList = data.platforms || [];
      setPlatforms(platformList);
      if (platformList.length > 0) {
        setSelectedPlatform(platformList[0]);
      }
    } catch (err: any) {
      console.error(err);
      setApiError(
        `Could not connect to the simulation server at ${API_BASE}. Make sure the FastAPI application is running.`,
      );
    }
  };

  const fetchUsers = async (platform: string) => {
    setLoadingUsers(true);
    setApiError("");
    try {
      const res = await fetch(
        `${API_BASE}/users?platform=${platform}&limit=50`,
      );
      if (!res.ok)
        throw new Error(`Could not fetch users for platform ${platform}`);
      const data = await res.json();
      setUsers(data.users || []);
      if (data.users && data.users.length > 0) {
        setSelectedUserId(data.users[0].composite_user_id);
      } else {
        setSelectedUserId("");
      }
    } catch (err: any) {
      console.error(err);
      setApiError(
        `Failed to load reviewer profiles for platform "${platform}".`,
      );
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) {
      alert("Please select a reviewer profile first.");
      return;
    }
    if (!itemName.trim() || !itemCategory.trim()) {
      alert("Please fill out at least the Item Name and Category.");
      return;
    }

    setLoadingSimulation(true);
    setApiError("");
    setSimulationResult(null);

    // Extract raw user_id from composite_user_id (format is platform_userId)
    const rawUserId = selectedUserId.includes("_")
      ? selectedUserId.split("_").slice(1).join("_")
      : selectedUserId;

    try {
      const payload = {
        platform: selectedPlatform,
        user_id: rawUserId,
        item: {
          name: itemName,
          category: itemCategory,
          location: itemLocation,
          price_range: itemPrice,
          description: itemDescription,
        },
        nigerian_context: nigerianContext,
      };

      const res = await fetch(`${API_BASE}/simulate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Simulation generation failed");
      }

      const data = await res.json();
      setSimulationResult(data);
    } catch (err: any) {
      console.error(err);
      setApiError(
        err.message || "An error occurred during simulation generation.",
      );
    } finally {
      setLoadingSimulation(false);
    }
  };

  // Preset loading helpers
  const loadPreset = (presetType: string) => {
    if (presetType === "chicken-republic") {
      setItemName("Chicken Republic");
      setItemCategory("Fast Food Restaurant");
      setItemLocation("Lekki Phase 1, Lagos");
      setItemPrice("Budget Friendly (₦)");
      setItemDescription(
        "Famous Nigerian fast food chain serving hot spicy chicken, Jollof rice, and fried rice with exceptional value.",
      );
      setNigerianContext(true);
    } else if (presetType === "lagoon") {
      setItemName("The Lagoon Restaurant");
      setItemCategory("Fine Dining / Seafood");
      setItemLocation("Victoria Island, Lagos");
      setItemPrice("Premium (₦₦₦)");
      setItemDescription(
        "Sleek waterfront restaurant with beautiful lagoon breezes, offering high-end continental courses, lobster, and cocktails.",
      );
      setNigerianContext(true);
    } else if (presetType === "argan-oil") {
      setItemName("Pure Cold-Pressed Moroccan Argan Oil");
      setItemCategory("Beauty & Hair Care");
      setItemLocation("Amazon Storefront");
      setItemPrice("Moderate ($$)");
      setItemDescription(
        "100% organic pure argan oil. Perfect moisturizer for softening hair, skin hydration, and nail cuticle restoration.",
      );
      setNigerianContext(false);
    } else if (presetType === "midnight-library") {
      setItemName("The Midnight Library (Hardcover)");
      setItemCategory("Fantasy / Fiction Book");
      setItemLocation("Goodreads Bookstore");
      setItemPrice("Moderate ($$)");
      setItemDescription(
        "A best-selling novel by Matt Haig exploring regret, decision-making, and what truly makes life worth living.",
      );
      setNigerianContext(false);
    }
  };

  // Helper to render stars beautifully
  const renderStarRating = (rating: number) => {
    const fullStars = Math.floor(rating);
    const hasHalf = rating % 1 >= 0.25 && rating % 1 <= 0.75;
    const extraFull = rating % 1 > 0.75 ? 1 : 0;
    const totalFull = fullStars + extraFull;

    return (
      <div className="flex items-center gap-0.5 text-amber-400">
        {[...Array(5)].map((_, i) => {
          if (i < totalFull) {
            return (
              <Star
                key={i}
                className="w-5 h-5 fill-amber-400 stroke-amber-400"
              />
            );
          } else if (i === totalFull && hasHalf) {
            return (
              <div key={i} className="relative w-5 h-5">
                <Star className="absolute top-0 left-0 w-5 h-5 text-slate-700 fill-slate-700 stroke-slate-700" />
                <div className="absolute top-0 left-0 w-[50%] h-full overflow-hidden">
                  <Star className="w-5 h-5 text-amber-400 fill-amber-400 stroke-amber-400" />
                </div>
              </div>
            );
          } else {
            return (
              <Star
                key={i}
                className="w-5 h-5 text-slate-700 fill-slate-700 stroke-slate-700"
              />
            );
          }
        })}
      </div>
    );
  };

  const getPlatformIcon = (platformName: string) => {
    switch (platformName.toLowerCase()) {
      case "yelp":
        return <Utensils className="w-4 h-4 text-rose-500" />;
      case "amazon":
        return <ShoppingBag className="w-4 h-4 text-amber-500" />;
      case "goodreads":
        return <BookOpen className="w-4 h-4 text-emerald-500" />;
      default:
        return <Globe className="w-4 h-4 text-sky-500" />;
    }
  };

  const getFriendlyReviewerStyle = (profile: UserProfile) => {
    if (profile.mean_rating >= 4.2) {
      return {
        label: "Usually very positive",
        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      };
    } else if (profile.mean_rating <= 2.8) {
      return {
        label: "Usually very critical",
        color: "text-rose-400 bg-rose-500/10 border-rose-500/20",
      };
    }

    if (profile.std_rating < 0.6) {
      return {
        label: "Very consistent rating style",
        color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
      };
    } else {
      return {
        label: "Balanced and detailed",
        color: "text-purple-400 bg-purple-500/10 border-purple-500/20",
      };
    }
  };

  // Filter users based on query
  const filteredUsers = users.filter((u) => {
    const rawId = u.composite_user_id.toLowerCase();
    const query = searchQuery.toLowerCase();
    return rawId.includes(query);
  });

  return (
    <div className="min-height-screen bg-[#070913] text-slate-100 flex flex-col font-sans">
      {/* Top Brand Banner */}
      <header className="border-b border-slate-900 bg-[#090d1a]/80 backdrop-blur-md sticky top-0 z-50 transition-all duration-300">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Sparkles className="w-5 h-5 text-[#070913]" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-250 to-slate-400 bg-clip-text text-transparent m-0 font-sans leading-none">
                Reviewer Simulator
              </h1>
              <p className="text-[10px] text-emerald-400 tracking-wider uppercase font-semibold font-mono mt-0.5">
                See what a specific customer would write about you
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#10b981]/10 text-emerald-400 border border-[#10b981]/15">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              Ready
            </span>
          </div>
        </div>
      </header>

      {/* Main Grid Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 flex flex-col gap-8">
        {/* Error Alert Display */}
        {apiError && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-start gap-3 shadow-lg shadow-rose-950/20 animate-fade-in">
            <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1.5">
              <p className="font-semibold">Connection Unavailable</p>
              <p className="opacity-90">{apiError}</p>
              <button
                onClick={fetchPlatforms}
                className="mt-2 text-xs font-semibold underline text-rose-400 hover:text-rose-300 transition flex items-center gap-1"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retry Connection
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* LEFT SIDEBAR: Service and User selector (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            {/* Step 1 Card: Reviewer Selection */}
            <div className="rounded-2xl border border-slate-900 bg-[#090d1a]/55 backdrop-blur-md p-6 flex flex-col gap-5 shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-900/80 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                    <User className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-100 text-base leading-tight">
                      1. Select a Reviewer
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Pick a person whose opinion you want to predict
                    </p>
                  </div>
                </div>
              </div>

              {/* Service Selector Tabs */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Select Service
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(platforms.length > 0
                    ? platforms
                    : ["yelp", "amazon", "goodreads"]
                  ).map((plat) => {
                    const isActive =
                      selectedPlatform.toLowerCase() === plat.toLowerCase();
                    return (
                      <button
                        key={plat}
                        type="button"
                        onClick={() => setSelectedPlatform(plat)}
                        className={`py-2.5 px-3 rounded-xl border text-xs font-semibold transition-all duration-200 flex flex-col items-center justify-center gap-1.5 uppercase tracking-wider ${
                          isActive
                            ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-400 shadow-md shadow-emerald-500/5"
                            : "border-slate-900 bg-slate-950/40 text-slate-400 hover:border-slate-800 hover:text-slate-200"
                        }`}
                      >
                        {getPlatformIcon(plat)}
                        <span>{plat}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* User Search & List Selection */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Choose a Reviewer
                  </label>
                  {users.length > 0 && (
                    <span className="text-[10px] text-slate-500 font-mono">
                      Loaded {users.length} reviewers
                    </span>
                  )}
                </div>

                <div className="relative">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search reviewer..."
                    className="w-full pl-10 pr-4 py-2 text-sm rounded-xl border border-slate-900 bg-slate-950/50 text-slate-200 focus:outline-none focus:border-emerald-500/40 focus:ring-1 focus:ring-emerald-500/40 transition placeholder-slate-600"
                  />
                </div>

                <div className="h-56 overflow-y-auto border border-slate-900/60 rounded-xl bg-slate-950/30 p-2 flex flex-col gap-1.5">
                  {loadingUsers ? (
                    <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs gap-2">
                      <RefreshCw className="w-5 h-5 animate-spin text-emerald-400" />
                      <span>Loading reviewers...</span>
                    </div>
                  ) : filteredUsers.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-slate-500 text-xs">
                      No reviewers found matching "{searchQuery}"
                    </div>
                  ) : (
                    filteredUsers.map((user) => {
                      const isSelected =
                        selectedUserId === user.composite_user_id;
                      // Extract clean ID for visual display
                      const friendlyId = user.composite_user_id.includes("_")
                        ? user.composite_user_id.split("_").slice(1).join("_")
                        : user.composite_user_id;

                      return (
                        <button
                          key={user.composite_user_id}
                          type="button"
                          onClick={() =>
                            setSelectedUserId(user.composite_user_id)
                          }
                          className={`w-full text-left p-3 rounded-xl border transition-all duration-150 flex items-center justify-between ${
                            isSelected
                              ? "bg-[#10b981]/5 border-[#10b981]/30 text-slate-100 ring-1 ring-emerald-500/20"
                              : "bg-transparent border-transparent text-slate-400 hover:bg-slate-900/40 hover:text-slate-200"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 overflow-hidden">
                            <div
                              className={`w-2 h-2 rounded-full ${isSelected ? "bg-emerald-400" : "bg-slate-700"}`}
                            ></div>
                            <div className="font-mono text-xs truncate max-w-[140px] md:max-w-none">
                              {friendlyId}
                            </div>
                          </div>

                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                              isSelected
                                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400 font-mono"
                                : "bg-slate-900/50 border-slate-800 text-slate-500"
                            }`}
                          >
                            {user.review_count} past reviews
                          </span>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            </div>

            {/* Quick Presets Utility Box */}
            <div className="rounded-2xl border border-slate-900 bg-[#090d1a]/55 backdrop-blur-md p-6 flex flex-col gap-4 shadow-xl">
              <div className="flex items-center gap-2 text-slate-350">
                <Info className="w-4 h-4 text-emerald-400" />
                <h4 className="font-semibold text-sm text-slate-250">
                  Try an Example
                </h4>
              </div>
              <p className="text-xs text-slate-400">
                Click any option below to instantly load its details.
              </p>
              <div className="flex flex-col gap-2">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => loadPreset("chicken-republic")}
                    className="p-2 rounded-xl bg-slate-950/65 border border-slate-900 text-left hover:border-emerald-500/30 transition flex flex-col gap-0.5"
                  >
                    <span className="text-[11px] font-bold text-slate-200 truncate">
                      🍗 Chicken Republic
                    </span>
                    <span className="text-[9px] text-emerald-400 font-medium">
                      Local Dining Style
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => loadPreset("lagoon")}
                    className="p-2 rounded-xl bg-slate-950/65 border border-slate-900 text-left hover:border-emerald-500/30 transition flex flex-col gap-0.5"
                  >
                    <span className="text-[11px] font-bold text-slate-200 truncate">
                      🦞 Lagoon VI Seafood
                    </span>
                    <span className="text-[9px] text-emerald-400 font-medium">
                      Local Dining Style
                    </span>
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => loadPreset("argan-oil")}
                    className="p-2 rounded-xl bg-slate-950/65 border border-slate-900 text-left hover:border-emerald-500/30 transition flex flex-col gap-0.5"
                  >
                    <span className="text-[11px] font-bold text-slate-200 truncate">
                      💧 Organic Argan Oil
                    </span>
                    <span className="text-[9px] text-amber-400 font-medium">
                      Beauty Product
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => loadPreset("midnight-library")}
                    className="p-2 rounded-xl bg-slate-950/65 border border-slate-900 text-left hover:border-emerald-500/30 transition flex flex-col gap-0.5"
                  >
                    <span className="text-[11px] font-bold text-slate-200 truncate">
                      📚 Midnight Library
                    </span>
                    <span className="text-[9px] text-emerald-400 font-medium">
                      Book Review
                    </span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT WORKSPACE: Input details and Output Simulation (7 cols) */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            {/* Step 2 Form Card */}
            <div className="rounded-2xl border border-slate-900 bg-[#090d1a]/55 backdrop-blur-md p-6 shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-900/80 pb-4 mb-5">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-100 text-base leading-tight">
                      2. Enter Product or Place Details
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Tell us what this person is going to review
                    </p>
                  </div>
                </div>
              </div>

              <form onSubmit={handleSimulate} className="space-y-4">
                {/* Product Name & Category */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Name of Product or Business
                    </label>
                    <input
                      type="text"
                      value={itemName}
                      onChange={(e) => setItemName(e.target.value)}
                      placeholder="e.g. KFC Lekki Drive-thru"
                      required
                      className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-900 bg-slate-950/40 text-slate-200 focus:outline-none focus:border-emerald-500/40 transition"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Category
                    </label>
                    <input
                      type="text"
                      value={itemCategory}
                      onChange={(e) => setItemCategory(e.target.value)}
                      placeholder="e.g. Fast Food"
                      required
                      className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-900 bg-slate-950/40 text-slate-200 focus:outline-none focus:border-emerald-500/40 transition"
                    />
                  </div>
                </div>

                {/* Location & Price Range */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Location (Optional)
                    </label>
                    <input
                      type="text"
                      value={itemLocation}
                      onChange={(e) => setItemLocation(e.target.value)}
                      placeholder="e.g. Lagos, Nigeria or Online Store"
                      className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-900 bg-slate-950/40 text-slate-200 focus:outline-none focus:border-emerald-500/40 transition"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Price Tier (Optional)
                    </label>
                    <select
                      value={itemPrice}
                      onChange={(e) => setItemPrice(e.target.value)}
                      className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-900 bg-slate-950/40 text-slate-200 focus:outline-none focus:border-emerald-500/40 transition appearance-none"
                    >
                      <option value="Budget Friendly (₦)">
                        Budget Friendly (₦)
                      </option>
                      <option value="Moderate ($$)">Moderate ($$)</option>
                      <option value="Premium ($$$)">Premium ($$$)</option>
                      <option value="Ultra-Luxe ($$$$)">
                        Ultra-Luxe ($$$$)
                      </option>
                    </select>
                  </div>
                </div>

                {/* Description */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Short Description (Optional)
                  </label>
                  <textarea
                    rows={3}
                    value={itemDescription}
                    onChange={(e) => setItemDescription(e.target.value)}
                    placeholder="Briefly describe what this product/service is, its pros and cons, or typical experience..."
                    className="w-full px-4 py-3 text-sm rounded-xl border border-slate-900 bg-slate-950/40 text-slate-200 focus:outline-none focus:border-emerald-500/40 transition resize-none"
                  />
                </div>

                {/* Nigerian Context Toggle Box */}
                <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-900 flex items-center justify-between gap-4 transition-all duration-200 hover:border-slate-800">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-bold text-slate-200">
                      Add Local Nigerian Writing Style
                    </span>
                    <span className="text-[10px] text-slate-400 leading-normal">
                      Make the review sound like it was written by a local consumer using local expressions.
                    </span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={nigerianContext}
                      onChange={(e) => setNigerianContext(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-350 after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500 peer-checked:after:bg-slate-950"></div>
                  </label>
                </div>

                {/* Trigger Button */}
                <button
                  type="submit"
                  disabled={loadingSimulation || !selectedUserId}
                  className={`w-full py-4 px-6 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 shadow-lg ${
                    loadingSimulation
                      ? "bg-slate-900 border border-slate-850 text-slate-400 cursor-not-allowed"
                      : !selectedUserId
                        ? "bg-slate-900 border border-slate-850 text-slate-500 cursor-not-allowed"
                        : "bg-emerald-500 text-slate-950 font-bold hover:bg-emerald-400 hover:shadow-emerald-500/10 cursor-pointer"
                  }`}
                >
                  {loadingSimulation ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Predicting review...
                    </>
                  ) : (
                    <>
                      <span>Predict Review</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Simulation Results Card */}
            {loadingSimulation && (
              <div className="rounded-2xl border border-slate-900 bg-[#090d1a]/55 p-12 flex flex-col items-center justify-center gap-4 shadow-xl min-h-[300px]">
                <div className="relative">
                  <div className="w-16 h-16 rounded-full border-2 border-emerald-500/10 border-t-2 border-t-emerald-400 animate-spin"></div>
                  <Sparkles className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6 text-emerald-400 animate-pulse" />
                </div>
                <div className="text-center space-y-1">
                  <h4 className="font-bold text-slate-100 text-sm">
                    Analyzing reviewer style...
                  </h4>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    Reading this reviewer's past ratings and reviews to predict their reaction to {itemName}...
                  </p>
                </div>
              </div>
            )}

            {simulationResult && !loadingSimulation && (
              <div className="space-y-6 animate-fade-in">
                {/* Result Section */}
                <div className="rounded-2xl border border-emerald-500/25 bg-[#0a0f1d] p-6 shadow-2xl shadow-emerald-500/5 flex flex-col gap-5">
                  <div className="flex items-center justify-between border-b border-slate-900/80 pb-4">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      <h4 className="font-bold text-slate-100 text-base">
                        Predicted Review
                      </h4>
                    </div>

                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                        simulationResult.confidence === "high"
                          ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                          : simulationResult.confidence === "medium"
                            ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
                            : "bg-rose-500/10 border-rose-500/20 text-rose-400"
                      }`}
                    >
                      Accuracy: {simulationResult.confidence}
                    </span>
                  </div>

                  {/* Predicted Rating Star Representation */}
                  <div className="p-4 rounded-xl bg-slate-950/65 border border-slate-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-0.5">
                      <span className="text-[10px] font-mono text-slate-450 uppercase tracking-widest">
                        Predicted Rating
                      </span>
                      <div className="flex items-center gap-2">
                        {renderStarRating(simulationResult.predicted_rating)}
                        <span className="text-lg font-bold text-slate-100 leading-none">
                          {simulationResult.predicted_rating.toFixed(1)}{" "}
                          <span className="text-xs text-slate-500">/ 5.0</span>
                        </span>
                      </div>
                    </div>

                    {/* User Profile quick summary */}
                    <div className="text-left sm:text-right space-y-0.5 border-t sm:border-t-0 sm:border-l border-slate-900 pt-3 sm:pt-0 sm:pl-5">
                      <span className="text-[10px] font-mono text-slate-450 uppercase tracking-widest">
                        Reviewer's Typical Rating
                      </span>
                      <p className="text-xs text-slate-300 font-semibold">
                        Usually rates items{" "}
                        {simulationResult.user_profile.mean_rating.toFixed(1)}{" "}
                        stars
                      </p>
                    </div>
                  </div>

                  {/* Simulated Review Text Display */}
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-mono text-slate-450 uppercase tracking-widest block">
                      Predicted Review Text
                    </span>
                    <div className="p-5 rounded-xl bg-slate-950/40 border border-slate-900/60 leading-relaxed text-slate-200 text-sm italic font-sans font-light">
                      "{typewriterText}"
                      {textEffectIndex <
                        simulationResult.simulated_review.length && (
                        <span className="inline-block w-1.5 h-3 bg-emerald-400 ml-0.5 animate-pulse"></span>
                      )}
                    </div>
                  </div>

                  {/* Reviewer DNA Insights */}
                  <div className="pt-2">
                    <span className="text-[10px] font-mono text-slate-450 uppercase tracking-widest block mb-2">
                      About this Reviewer
                    </span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="p-3.5 rounded-xl bg-slate-950/30 border border-slate-900/40 flex flex-col gap-1">
                        <span className="text-[10px] text-slate-450 uppercase tracking-wide">
                          Rating Style
                        </span>
                        <span
                          className={`inline-flex self-start items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border ${
                            getFriendlyReviewerStyle(
                              simulationResult.user_profile,
                            ).color
                          }`}
                        >
                          {
                            getFriendlyReviewerStyle(
                              simulationResult.user_profile,
                            ).label
                          }
                        </span>
                      </div>

                      <div className="p-3.5 rounded-xl bg-slate-950/30 border border-slate-900/40 flex flex-col gap-1">
                        <span className="text-[10px] text-slate-450 uppercase tracking-wide font-mono">
                          Typical Review Length
                        </span>
                        <span className="text-xs font-semibold text-slate-200 capitalize">
                          Writes{" "}
                          {simulationResult.user_profile.typical_review_length}{" "}
                          reviews
                        </span>
                      </div>
                    </div>

                    {simulationResult.user_profile.common_themes.length > 0 && (
                      <div className="mt-3.5">
                        <span className="text-[10px] text-slate-450 uppercase tracking-wide block mb-1.5">
                          Common topics mentioned:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {simulationResult.user_profile.common_themes.map(
                            (theme, i) => (
                              <span
                                key={i}
                                className="text-[10px] px-2.5 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-slate-400 font-semibold"
                              >
                                {theme}
                              </span>
                            ),
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Source past reviews written by the selected user */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-slate-100 text-sm">
                        Actual Past Reviews by this Reviewer
                      </h4>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Here are actual reviews this person has written for similar items.
                      </p>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-950 border border-slate-900 text-slate-500 font-mono">
                      {simulationResult.retrieved_reviews_used.length} similar reviews found
                    </span>
                  </div>

                  <div className="grid grid-cols-1 gap-4">
                    {simulationResult.retrieved_reviews_used.map((rev, idx) => (
                      <div
                        key={idx}
                        className="rounded-xl border border-slate-900 bg-[#090d1a]/30 p-4 flex flex-col gap-3 transition hover:border-slate-800"
                      >
                        <div className="flex items-start justify-between border-b border-slate-900/50 pb-2">
                          <div>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/10 text-emerald-400 font-semibold uppercase tracking-wider font-mono">
                              {rev.platform}
                            </span>
                            <h5 className="font-bold text-slate-200 text-xs mt-1.5">
                              {rev.item_name}
                            </h5>
                            <p className="text-[10px] text-slate-450 mt-0.5">
                              {rev.item_category}
                            </p>
                          </div>

                          <div className="flex items-center gap-1.5">
                            {renderStarRating(rev.rating)}
                            <span className="text-xs font-bold text-slate-300 font-mono">
                              {rev.rating.toFixed(1)}
                            </span>
                          </div>
                        </div>

                        <p className="text-xs text-slate-350 leading-relaxed italic">
                          "{rev.review_text}"
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Unstarted Placeholder */}
            {!simulationResult && !loadingSimulation && (
              <div className="rounded-2xl border border-dashed border-slate-900 bg-[#090d1a]/20 p-16 flex flex-col items-center justify-center gap-4 text-center shadow-inner min-h-[350px]">
                <div className="w-12 h-12 rounded-xl bg-slate-900/80 border border-slate-850 flex items-center justify-center text-slate-500">
                  <Sparkles className="w-5 h-5 text-slate-600" />
                </div>
                <div className="space-y-1">
                  <h4 className="font-semibold text-slate-300 text-sm">
                    Ready to Predict
                  </h4>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto leading-normal">
                    Select a reviewer on the left, enter details of a product or service, and click 'Predict Review' to see what they would say.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer Branding */}
      <footer className="border-t border-slate-900/60 bg-[#060812] py-8 text-center text-slate-550 text-xs">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="font-mono text-[10px]">
            &copy; 2026 Reviewer Simulator. Built with React + Tailwind.
          </p>
          <div className="flex items-center gap-4 font-mono text-[10px]">
            <span>
              Status: <span className="text-emerald-400">Ready</span>
            </span>
            <span>
              Port: <span className="text-slate-350">8000</span>
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
