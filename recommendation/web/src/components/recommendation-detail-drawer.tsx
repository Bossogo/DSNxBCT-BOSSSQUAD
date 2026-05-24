import React from 'react';
import { X, Star, ExternalLink, ShieldCheck, Tag, MapPin } from 'lucide-react';

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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  item_metadata?: Record<string, any>;
}

interface RecommendationDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  item: RecommendationItem | null;
}

export const RecommendationDetailDrawer: React.FC<RecommendationDetailDrawerProps> = ({
  isOpen,
  onClose,
  item,
}) => {
  if (!item) return null;

  const platformColors: Record<string, string> = {
    amazon: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    yelp: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    goodreads: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  };

  const platformUrl = item.platform.toLowerCase() === 'amazon' 
    ? `https://www.amazon.com/s?k=${encodeURIComponent(item.item_name)}`
    : item.platform.toLowerCase() === 'yelp'
    ? `https://www.yelp.com/search?find_desc=${encodeURIComponent(item.item_name)}`
    : `https://www.goodreads.com/search?q=${encodeURIComponent(item.item_name)}`;

  // Parse images if present in metadata
  const imageUrls = item.item_metadata?.images || item.item_metadata?.image_url;
  const imageUrl = Array.isArray(imageUrls) ? imageUrls[0] : imageUrls;

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-50 bg-black/60 backdrop-blur-xs transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 z-50 h-full w-full max-w-md border-l border-slate-800 bg-[#0f172a] shadow-2xl transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 p-4">
            <h2 className="text-lg font-semibold text-slate-100 font-sans">Item Details</h2>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
              aria-label="Close panel"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Main Visuals & Title */}
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${platformColors[item.platform.toLowerCase()] || 'bg-slate-800 text-slate-400 border-slate-700'}`}>
                    {item.platform}
                  </span>
                  <h3 className="mt-2 text-xl font-bold text-slate-100 leading-snug">
                    {item.item_name}
                  </h3>
                  <p className="text-sm text-indigo-400 font-medium mt-1">{item.item_category}</p>
                  {(item.item_metadata?.address || item.item_metadata?.city) && (
                    <div className="flex items-start gap-1.5 mt-2 text-xs text-slate-400 leading-relaxed">
                      <MapPin className="h-4 w-4 text-rose-500 shrink-0 mt-0.5" />
                      <span>
                        {[item.item_metadata.address, item.item_metadata.city, item.item_metadata.state].filter(Boolean).join(', ')}
                      </span>
                    </div>
                  )}
                </div>
                {item.rank && (
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-bold text-lg">
                    #{item.rank}
                  </div>
                )}
              </div>

              {/* Product Image placeholder or real image if exists */}
              {imageUrl ? (
                <div className="aspect-video w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50">
                  <img
                    src={imageUrl}
                    alt={item.item_name}
                    className="h-full w-full object-contain p-2"
                  />
                </div>
              ) : (
                <div className="aspect-video w-full rounded-xl border border-dashed border-slate-800 bg-slate-900/25 flex flex-col items-center justify-center text-slate-500">
                  <span className="text-xs uppercase tracking-wider font-semibold">Product Image</span>
                  <span className="text-2xs text-slate-600 mt-1">Image not available in dataset</span>
                </div>
              )}
            </div>

            {/* Ratings & Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 p-4 text-center">
                <div className="flex items-center justify-center gap-1 text-amber-400">
                  <Star className="h-5 w-5 fill-current" />
                  <span className="text-lg font-bold text-slate-100">{item.avg_rating}</span>
                </div>
                <p className="text-2xs text-slate-500 font-medium uppercase tracking-wider mt-1">Average Rating</p>
              </div>
              <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 p-4 text-center">
                <span className="text-lg font-bold text-slate-100">{item.review_count || 0}</span>
                <p className="text-2xs text-slate-500 font-medium uppercase tracking-wider mt-1">Total Reviews</p>
              </div>
            </div>

            {/* Match Reason */}
            <div className="rounded-xl border border-indigo-500/15 bg-indigo-500/5 p-4 space-y-2">
              <div className="flex items-center gap-2 text-indigo-400 font-medium text-xs">
                <ShieldCheck className="h-4 w-4" />
                <span>Recommendation Context</span>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed italic">
                "{item.match_reason}"
              </p>
            </div>

            {/* Keywords */}
            {item.top_keywords && item.top_keywords.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Tag className="h-3.5 w-3.5" />
                  <span>Key Attributes</span>
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {item.top_keywords.map((keyword) => (
                    <span
                      key={keyword}
                      className="rounded-md bg-slate-800/60 px-2 py-1 text-xs text-slate-300 border border-slate-700/50"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Details & Metadata */}
            {item.item_metadata && Object.keys(item.item_metadata).length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Specifications
                </h4>
                <div className="rounded-xl border border-slate-800 bg-slate-900/10 p-4 space-y-3 text-sm">
                  {Object.entries(item.item_metadata).map(([key, val]) => {
                    if (key === 'images' || key === 'image_url') return null;
                    
                    const formattedKey = key
                      .replace(/_/g, ' ')
                      .replace(/\b\w/g, (char) => char.toUpperCase());

                    let displayVal: string;
                    if (Array.isArray(val)) {
                      displayVal = val.join(', ');
                    } else if (typeof val === 'object') {
                      displayVal = JSON.stringify(val);
                    } else {
                      displayVal = String(val);
                    }

                    if (displayVal.length > 250) {
                      displayVal = displayVal.substring(0, 247) + '...';
                    }

                    if (!displayVal || displayVal === 'N/A') return null;

                    return (
                      <div key={key} className="flex flex-col space-y-1">
                        <span className="text-xs font-semibold text-slate-500">{formattedKey}</span>
                        <span className="text-slate-300 leading-normal">{displayVal}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Footer Action */}
          <div className="border-t border-slate-800 p-4 bg-[#0a0f1d]">
            <a
              href={platformUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 active:bg-indigo-700 transition-colors"
            >
              <span>View on {item.platform}</span>
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
    </>
  );
};
