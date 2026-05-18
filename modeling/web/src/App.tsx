import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Globe,
  Loader2,
  RefreshCw,
  Search,
  ShoppingBag,
  Sparkles,
  Star,
  Utensils,
} from "lucide-react";

import heroArtwork from "./assets/hero.png";
import "./App.css";

const API_BASE = "http://localhost:8000";
const FALLBACK_PLATFORMS = ["yelp", "amazon", "goodreads"];

const PRICE_OPTIONS = [
  { value: "Budget Friendly (₦)", label: "Budget" },
  { value: "Moderate ($$)", label: "Mid-range" },
  { value: "Premium ($$$)", label: "Premium" },
  { value: "Ultra-Luxe ($$$$)", label: "Luxury" },
];

const PRESETS = [
  {
    id: "chicken-republic",
    title: "Chicken Republic",
    category: "Fast food restaurant",
    location: "Lekki Phase 1, Lagos",
    price: "Budget Friendly (₦)",
    description:
      "A familiar local spot for quick chicken, rice, and a reliable everyday meal.",
    localTone: true,
  },
  {
    id: "lagoon",
    title: "The Lagoon Restaurant",
    category: "Seafood and fine dining",
    location: "Victoria Island, Lagos",
    price: "Premium ($$$)",
    description:
      "A polished waterfront dining experience with seafood, cocktails, and a relaxed evening atmosphere.",
    localTone: true,
  },
  {
    id: "argan-oil",
    title: "Pure Cold-Pressed Argan Oil",
    category: "Beauty and hair care",
    location: "Online store",
    price: "Moderate ($$)",
    description:
      "A simple natural oil for hair softness, skin hydration, and everyday care.",
    localTone: false,
  },
  {
    id: "midnight-library",
    title: "The Midnight Library",
    category: "Novel",
    location: "Bookshop",
    price: "Moderate ($$)",
    description:
      "A thoughtful story about regret, choice, and the different versions of a life.",
    localTone: false,
  },
] as const;

interface RetrievedReview {
  item_name: string;
  item_category: string;
  review_text: string;
  rating: number;
  platform: string;
  item_metadata?: Record<string, unknown>;
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

function friendlyLabel(value: string) {
  return value
    .replace(/^.*?_/, "")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function platformLabel(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function platformHint(value: string) {
  switch (value.toLowerCase()) {
    case "yelp":
      return "Dining and local places";
    case "amazon":
      return "Shopping";
    case "goodreads":
      return "Books";
    default:
      return "Everyday choices";
  }
}

function platformIcon(value: string) {
  switch (value.toLowerCase()) {
    case "yelp":
      return <Utensils className="platform-icon" />;
    case "amazon":
      return <ShoppingBag className="platform-icon" />;
    case "goodreads":
      return <BookOpen className="platform-icon" />;
    default:
      return <Globe className="platform-icon" />;
  }
}

function priceLabel(value: string) {
  return PRICE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

function confidenceLabel(value: string) {
  switch (value) {
    case "high":
      return "Strong match";
    case "medium":
      return "Fair match";
    default:
      return "Light match";
  }
}

function reviewerTone(profile: UserProfile) {
  if (profile.mean_rating >= 4.2) {
    return {
      label: "Usually upbeat",
      className: "tone tone-positive",
    };
  }

  if (profile.mean_rating <= 2.8) {
    return {
      label: "Usually picky",
      className: "tone tone-critical",
    };
  }

  if (profile.std_rating < 0.6) {
    return {
      label: "Very consistent",
      className: "tone tone-consistent",
    };
  }

  return {
    label: "Balanced and detailed",
    className: "tone tone-balanced",
  };
}

function Stars({ rating }: { rating: number }) {
  const fullStars = Math.floor(rating);
  const hasHalf = rating % 1 >= 0.25 && rating % 1 <= 0.75;
  const totalFull = fullStars + (rating % 1 > 0.75 ? 1 : 0);

  return (
    <div className="stars" aria-label={`${rating.toFixed(1)} out of 5`}>
      {[...Array(5)].map((_, index) => {
        if (index < totalFull) {
          return <Star key={index} className="star star-full" />;
        }

        if (index === totalFull && hasHalf) {
          return (
            <span key={index} className="star-half">
              <Star className="star star-empty" />
              <span className="star-half-fill">
                <Star className="star star-full" />
              </span>
            </span>
          );
        }

        return <Star key={index} className="star star-empty" />;
      })}
    </div>
  );
}

export default function App() {
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("");
  const [users, setUsers] = useState<UserSelectorItem[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [message, setMessage] = useState("");

  const [itemName, setItemName] = useState("");
  const [itemCategory, setItemCategory] = useState("");
  const [itemLocation, setItemLocation] = useState("");
  const [itemPrice, setItemPrice] = useState("Moderate ($$)");
  const [itemDescription, setItemDescription] = useState("");
  const [useLocalTone, setUseLocalTone] = useState(false);

  const [result, setResult] = useState<SimulateResponse | null>(null);

  useEffect(() => {
    void fetchPlatforms();
  }, []);

  useEffect(() => {
    if (selectedPlatform) {
      void fetchUsers(selectedPlatform);
    }
  }, [selectedPlatform]);

  const selectedUser = useMemo(
    () => users.find((user) => user.composite_user_id === selectedUserId),
    [users, selectedUserId],
  );

  const filteredUsers = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return users;
    return users.filter((user) =>
      friendlyLabel(user.composite_user_id).toLowerCase().includes(query),
    );
  }, [users, searchQuery]);

  async function fetchPlatforms() {
    try {
      setMessage("");
      const response = await fetch(`${API_BASE}/platforms`);
      if (!response.ok) {
        throw new Error("Could not load places");
      }

      const data = (await response.json()) as { platforms?: string[] };
      const list = data.platforms?.length ? data.platforms : FALLBACK_PLATFORMS;
      setPlatforms(list);
      setSelectedPlatform((current) => current || list[0]);
    } catch (error) {
      console.error(error);
      setPlatforms(FALLBACK_PLATFORMS);
      setSelectedPlatform((current) => current || FALLBACK_PLATFORMS[0]);
      setMessage(
        `We could not reach the local preview server at ${API_BASE}. Some choices may still load once it is back online.`,
      );
    }
  }

  async function fetchUsers(platform: string) {
    setLoadingUsers(true);
    setMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/users?platform=${encodeURIComponent(platform)}&limit=50`,
      );
      if (!response.ok) {
        throw new Error(`Could not load people for ${platform}`);
      }

      const data = (await response.json()) as {
        users?: UserSelectorItem[];
      };
      const list = data.users ?? [];
      setUsers(list);

      setSelectedUserId((current) => {
        if (current && list.some((user) => user.composite_user_id === current)) {
          return current;
        }
        return list[0]?.composite_user_id ?? "";
      });
    } catch (error) {
      console.error(error);
      setUsers([]);
      setSelectedUserId("");
      setMessage(
        `We could not load the people list for ${platformLabel(platform)} right now.`,
      );
    } finally {
      setLoadingUsers(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedUserId) {
      setMessage("Pick a person first so we have a voice to work from.");
      return;
    }

    if (!itemName.trim() || !itemCategory.trim()) {
      setMessage("Add a name and a category to continue.");
      return;
    }

    const rawUserId = selectedUserId.includes("_")
      ? selectedUserId.split("_").slice(1).join("_")
      : selectedUserId;

    setLoadingPreview(true);
    setMessage("");
    setResult(null);

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
        nigerian_context: useLocalTone,
      };

      const response = await fetch(`${API_BASE}/simulate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorBody = (await response.json().catch(() => ({}))) as {
          detail?: string;
        };
        throw new Error(errorBody.detail || "Preview failed");
      }

      const data = (await response.json()) as SimulateResponse;
      setResult(data);
    } catch (error) {
      console.error(error);
      setMessage(
        error instanceof Error
          ? error.message
          : "We could not build the preview right now.",
      );
    } finally {
      setLoadingPreview(false);
    }
  }

  function loadPreset(presetId: string) {
    const preset = PRESETS.find((item) => item.id === presetId);
    if (!preset) return;

    setItemName(preset.title);
    setItemCategory(preset.category);
    setItemLocation(preset.location);
    setItemPrice(preset.price);
    setItemDescription(preset.description);
    setUseLocalTone(preset.localTone);
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <div className="page">
        <header className="hero">
          <div className="hero-copy">
            <span className="eyebrow">
              <Sparkles className="eyebrow-icon" />
              Friendly preview flow
            </span>
            <h1>See the kind of response a real person might give.</h1>
            <p>
              Pick a place, choose a person, and describe what they are looking
              at. The flow stays calm and simple from start to finish.
            </p>

            <div className="hero-actions">
              <button
                type="button"
                className="primary-button"
                onClick={() =>
                  document
                    .getElementById("builder")
                    ?.scrollIntoView({ behavior: "smooth", block: "start" })
                }
              >
                Start here
                <ArrowRight className="button-icon" />
              </button>
              <div className="hero-note">Three steps. No clutter.</div>
            </div>
          </div>

          <figure className="hero-card" aria-hidden="true">
            <div className="hero-card-image-wrap">
              <img src={heroArtwork} alt="" className="hero-card-image" />
            </div>
            <figcaption className="hero-card-footer">
              <div>
                <span className="hero-card-label">What you get</span>
                <strong>A clean preview of the likely response</strong>
              </div>
              <div className="hero-card-meta">
                <span>Warm</span>
                <span>Human</span>
                <span>Simple</span>
              </div>
            </figcaption>
          </figure>
        </header>

        {message ? (
          <section className="notice" aria-live="polite">
            <AlertCircle className="notice-icon" />
            <div>
              <strong>Something needs attention</strong>
              <p>{message}</p>
            </div>
            <button type="button" className="notice-action" onClick={fetchPlatforms}>
              <RefreshCw className="button-icon" />
              Try again
            </button>
          </section>
        ) : null}

        <main className="layout" id="builder">
          <aside className="panel">
            <div className="panel-inner">
              <div className="section-head">
                <span className="step-number">1</span>
                <div>
                  <h2>Choose a place</h2>
                  <p>Start with the place that fits your scenario.</p>
                </div>
              </div>

              <div className="platform-list" role="list" aria-label="Choose a place">
                {(platforms.length ? platforms : FALLBACK_PLATFORMS).map((platform) => {
                  const active = selectedPlatform === platform;
                  return (
                    <button
                      key={platform}
                      type="button"
                      className={`platform-button${active ? " is-active" : ""}`}
                      onClick={() => {
                        setSearchQuery("");
                        setResult(null);
                        setSelectedPlatform(platform);
                      }}
                    >
                      <span className="platform-icon-wrap">{platformIcon(platform)}</span>
                      <span className="platform-copy">
                        <strong>{platformLabel(platform)}</strong>
                        <span>{platformHint(platform)}</span>
                      </span>
                      <ChevronRight className="platform-arrow" />
                    </button>
                  );
                })}
              </div>

              <div className="section-head section-head-spaced">
                <span className="step-number">2</span>
                <div>
                  <h2>Pick a person</h2>
                  <p>Search by the person’s label or id fragment.</p>
                </div>
              </div>

              <label className="search-field">
                <Search className="search-icon" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search the list"
                />
              </label>

              <div className="user-meta">
                <span>{users.length || "No"} people available</span>
                {selectedUser ? (
                  <span>Selected: {friendlyLabel(selectedUser.composite_user_id)}</span>
                ) : null}
              </div>

              <div className="user-list" aria-live="polite">
                {loadingUsers ? (
                  <div className="empty-state">
                    <Loader2 className="spin-icon" />
                    <p>Loading people…</p>
                  </div>
                ) : filteredUsers.length ? (
                  filteredUsers.map((user) => {
                    const active = user.composite_user_id === selectedUserId;
                    return (
                      <button
                        key={user.composite_user_id}
                        type="button"
                        className={`user-button${active ? " is-active" : ""}`}
                        onClick={() => {
                          setSelectedUserId(user.composite_user_id);
                          setResult(null);
                        }}
                      >
                        <span className="user-name">
                          {friendlyLabel(user.composite_user_id)}
                        </span>
                        <span className="user-count">{user.review_count} examples</span>
                      </button>
                    );
                  })
                ) : (
                  <div className="empty-state">
                    <p>No matches for “{searchQuery}”.</p>
                  </div>
                )}
              </div>

              <div className="preset-box">
                <div className="section-head preset-head">
                  <div>
                    <h2>Quick starts</h2>
                    <p>Use one of these to fill the form fast.</p>
                  </div>
                </div>

                <div className="preset-grid">
                  {PRESETS.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      className="preset-button"
                      onClick={() => loadPreset(preset.id)}
                    >
                      <strong>{preset.title}</strong>
                      <span>{preset.category}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </aside>

          <section className="panel content-panel">
            <div className="panel-inner">
              <div className="section-head">
                <span className="step-number">3</span>
                <div>
                  <h2>Describe what they are looking at</h2>
                  <p>Keep it simple. The form only asks for what matters.</p>
                </div>
              </div>

              <form className="form-grid" onSubmit={handleSubmit}>
                <div className="field-row">
                  <label className="field">
                    <span>Name</span>
                    <input
                      type="text"
                      value={itemName}
                      onChange={(event) => setItemName(event.target.value)}
                      placeholder="e.g. a café, product, or service"
                      required
                    />
                  </label>

                  <label className="field">
                    <span>Category</span>
                    <input
                      type="text"
                      value={itemCategory}
                      onChange={(event) => setItemCategory(event.target.value)}
                      placeholder="e.g. café, book, skincare"
                      required
                    />
                  </label>
                </div>

                <div className="field-row">
                  <label className="field">
                    <span>Where it is</span>
                    <input
                      type="text"
                      value={itemLocation}
                      onChange={(event) => setItemLocation(event.target.value)}
                      placeholder="Optional"
                    />
                  </label>

                  <label className="field">
                    <span>Price feel</span>
                    <select
                      value={itemPrice}
                      onChange={(event) => setItemPrice(event.target.value)}
                    >
                      {PRICE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <span className="field-hint">{priceLabel(itemPrice)}</span>
                  </label>
                </div>

                <label className="field">
                  <span>Extra context</span>
                  <textarea
                    rows={4}
                    value={itemDescription}
                    onChange={(event) => setItemDescription(event.target.value)}
                    placeholder="A short note about the experience, look, quality, or anything else that matters."
                  />
                </label>

                <div className="tone-box">
                  <div>
                    <strong>Use local phrasing</strong>
                    <p>Turn on a more local, everyday writing style.</p>
                  </div>
                  <label className="switch">
                    <input
                      type="checkbox"
                      checked={useLocalTone}
                      onChange={(event) => setUseLocalTone(event.target.checked)}
                    />
                    <span />
                  </label>
                </div>

                <button
                  type="submit"
                  className="primary-button submit-button"
                  disabled={loadingPreview || !selectedUserId}
                >
                  {loadingPreview ? (
                    <>
                      <Loader2 className="button-icon spin-icon" />
                      Building preview…
                    </>
                  ) : (
                    <>
                      Show preview
                      <ArrowRight className="button-icon" />
                    </>
                  )}
                </button>
              </form>

              <div className="preview-card">
                <div className="section-head section-head-spaced">
                  <span className="step-number">4</span>
                  <div>
                    <h2>Your preview</h2>
                    <p>A clear, readable outcome once the form is submitted.</p>
                  </div>
                </div>

                {loadingPreview ? (
                  <div className="loading-state" aria-live="polite">
                    <Loader2 className="spin-icon loading-spin" />
                    <strong>Putting the response together…</strong>
                    <p>We are using the selected person’s style to shape the preview.</p>
                  </div>
                ) : result ? (
                  <div className="result-stack">
                    <section className="result-hero">
                      <div className="result-rating">
                        <span className="eyebrow tiny">
                          <CheckCircle2 className="eyebrow-icon" />
                          {confidenceLabel(result.confidence)}
                        </span>
                        <div className="rating-line">
                          <Stars rating={result.predicted_rating} />
                          <strong>{result.predicted_rating.toFixed(1)}</strong>
                        </div>
                      </div>

                      <div className="result-mirror">
                        <div>
                          <span className="result-label">Usually rates around</span>
                          <strong>{result.user_profile.mean_rating.toFixed(1)} / 5</strong>
                        </div>
                        <div>
                          <span className="result-label">Typical length</span>
                          <strong>{result.user_profile.typical_review_length}</strong>
                        </div>
                        <div>
                          <span className="result-label">Price feel</span>
                          <strong>{priceLabel(itemPrice)}</strong>
                        </div>
                      </div>
                    </section>

                    <section className="quote-card">
                      <span className="result-label">Preview text</span>
                      <p>“{result.simulated_review}”</p>
                    </section>

                    <section className="insight-grid">
                      <article className="insight-card">
                        <span className="result-label">Style</span>
                        <strong>{reviewerTone(result.user_profile).label}</strong>
                        <span className={reviewerTone(result.user_profile).className}>
                          {reviewerTone(result.user_profile).label}
                        </span>
                      </article>
                      <article className="insight-card">
                        <span className="result-label">What they mention most</span>
                        <div className="chip-row">
                          {result.user_profile.common_themes.length ? (
                            result.user_profile.common_themes.map((theme) => (
                              <span key={theme} className="chip">
                                {theme}
                              </span>
                            ))
                          ) : (
                            <span className="chip muted">No recurring themes yet</span>
                          )}
                        </div>
                      </article>
                    </section>

                    <section className="examples-block">
                      <div className="section-head section-head-inline">
                        <div>
                          <h3>Similar examples from their history</h3>
                          <p>
                            {result.retrieved_reviews_used.length} past examples helped
                            shape this preview.
                          </p>
                        </div>
                      </div>

                      <div className="example-list">
                        {result.retrieved_reviews_used.map((review, index) => (
                          <article key={`${review.item_name}-${index}`} className="example-card">
                            <div className="example-top">
                              <div>
                                <span className="example-source">
                                  {platformLabel(review.platform)}
                                </span>
                                <h4>{review.item_name}</h4>
                                <p>{review.item_category}</p>
                              </div>
                              <div className="example-rating">
                                <Stars rating={review.rating} />
                                <strong>{review.rating.toFixed(1)}</strong>
                              </div>
                            </div>
                            <p className="example-quote">“{review.review_text}”</p>
                          </article>
                        ))}
                      </div>
                    </section>
                  </div>
                ) : (
                  <div className="empty-preview">
                    <Sparkles className="empty-icon" />
                    <strong>Ready when you are</strong>
                    <p>
                      Pick a place, choose a person, and add a few details to see the
                      preview appear here.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </section>
        </main>

        <footer className="footer">
          <span>Human-friendly preview flow</span>
          <span>React + Tailwind + FastAPI</span>
        </footer>
      </div>
    </div>
  );
}
