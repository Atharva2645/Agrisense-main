import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp,
  ChevronDown,
  RefreshCw,
} from 'lucide-react';

export const MarketPricePage = ({
  initialCommodity = '',
  initialDistrict = '',
  initialGrade = 'B',
  commodityLocked = false,
  onNavigate,
}) => {
  const GRADES = ['A', 'B', 'C'];
  const [commodity, setCommodity] = useState(initialCommodity);
  const [district, setDistrict] = useState(initialDistrict);
  const [grade, setGrade] = useState(GRADES.includes(initialGrade) ? initialGrade : 'B');
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  const fetchMarketData = useCallback(async (signal) => {
    if (!commodity || !district) {
      setMarketData(null);
      setError('');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError('');
    try {
      const query = new URLSearchParams({ commodity, district });
      const response = await fetch(`/api/market-prices?${query}`, { signal });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to load mandi prices.');
      }
      setMarketData(data);
    } catch (fetchError) {
      if (fetchError.name !== 'AbortError') {
        setError(fetchError.message || 'Failed to load mandi prices.');
      }
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [commodity, district]);

  useEffect(() => {
    const controller = new AbortController();
    fetchMarketData(controller.signal);
    const refreshInterval = setInterval(
      () => fetchMarketData(controller.signal),
      5 * 60 * 1000
    );
    return () => {
      clearInterval(refreshInterval);
      controller.abort();
    };
  }, [fetchMarketData, refreshKey]);

  const currentMarketData =
    marketData?.commodity === commodity && marketData?.district === district
      ? marketData
      : null;
  const summary = currentMarketData?.summary;
  const gradePrices = currentMarketData?.gradePrices || null;
  const selectedGradePrice = gradePrices?.[grade] || null;
  const comparisons = currentMarketData?.comparisons || [];
  const gradeLabel = { A: 'Premium', B: 'Standard', C: 'Economy' };
  const displayPrice = (price) => price == null ? '—' : Number(price).toFixed(2);
  const reportDate = currentMarketData?.dataDate
    ? new Date(`${currentMarketData.dataDate}T00:00:00Z`).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        timeZone: 'UTC'
      })
    : null;
  const lastChecked = currentMarketData?.fetchedAt
    ? new Date(currentMarketData.fetchedAt).toLocaleTimeString()
    : null;

  return (
    <div className="w-full space-y-6">
      {/* Title & APMC Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-emerald-100/70">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-emerald-800 uppercase tracking-wide">
            <TrendingUp className="w-4 h-4 text-emerald-600" />
            <span>Reported APMC Mandi Prices</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mt-0.5 font-['Space_Grotesk']">
            {commodity} Grade {grade} Prices — {district}
          </h1>
          <p className="text-xs text-slate-500 font-medium">
            Latest available market reports · AGMARKNET via data.gov.in
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setRefreshKey((key) => key + 1)}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-200 bg-white px-3 py-1.5 text-xs font-bold text-emerald-800 hover:bg-emerald-50 disabled:cursor-wait disabled:opacity-60"
            aria-label="Refresh mandi prices"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Refreshing' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="text-xs text-slate-500" role="status" aria-live="polite">
        {loading && !currentMarketData && 'Loading reported mandi prices…'}
        {error && <span className="text-red-700">{error} </span>}
        {!error && currentMarketData?.dataDate && (
          <span>
            Latest market date: {reportDate} · Checked: {lastChecked} · Auto-refreshes every 5 minutes · Source: {currentMarketData.source}
          </span>
        )}
        {!error && currentMarketData && !currentMarketData.dataDate && currentMarketData.message}
      </div>

      {/* Top Filter Bar */}
      <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          {/* Commodity */}
          <div>
            <label className="block text-[11px] font-extrabold text-slate-700 uppercase tracking-wider mb-1.5">
              Select Commodity
            </label>
            <div className="relative">
              <select
                value={commodity}
                onChange={(e) => setCommodity(e.target.value)}
                disabled={commodityLocked}
                className="w-full px-4 py-2.5 text-xs font-bold rounded-xl border border-slate-200 bg-white focus:border-emerald-600 focus:ring-4 focus:ring-emerald-500/10 outline-none appearance-none cursor-pointer shadow-2xs text-slate-900 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-600"
              >
                <option value="" disabled>Select a commodity</option>
                <option value="Tomato">Tomato 🍅</option>
                <option value="Apple">Apple 🍎</option>
                <option value="Dragon Fruit">Dragon Fruit</option>
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-3 pointer-events-none" />
            </div>
            {commodityLocked && (
              <p className="mt-1.5 text-[10px] font-medium text-slate-500">
                Selected automatically from your produce analysis.
              </p>
            )}
          </div>

          {/* District */}
          <div>
            <label className="block text-[11px] font-extrabold text-slate-700 uppercase tracking-wider mb-1.5">
              APMC Mandi District
            </label>
            <div className="relative">
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="w-full px-4 py-2.5 text-xs font-bold rounded-xl border border-slate-200 bg-white focus:border-emerald-600 focus:ring-4 focus:ring-emerald-500/10 outline-none appearance-none cursor-pointer shadow-2xs text-slate-900"
              >
                <option value="" disabled>Select a district</option>
                <option value="Kolhapur">Kolhapur (Maharashtra)</option>
                <option value="Nashik">Nashik (Maharashtra)</option>
                <option value="Pune">Pune (Maharashtra)</option>
                <option value="Shimla">Shimla (Himachal Pradesh)</option>
                <option value="Sangli">Sangli (Maharashtra)</option>
                <option value="Satara">Satara (Maharashtra)</option>
                <option value="Solapur">Solapur (Maharashtra)</option>
                <option value="Ahmednagar">Ahmednagar (Maharashtra)</option>
                <option value="Nagpur">Nagpur (Maharashtra)</option>
                <option value="Bengaluru">Bengaluru (Karnataka)</option>
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-3 pointer-events-none" />
            </div>
          </div>

          {/* Grade */}
          <div>
            <label className="block text-[11px] font-extrabold text-slate-700 uppercase tracking-wider mb-1.5">
              Produce Grade
            </label>
            <div className="grid grid-cols-3 gap-1.5" role="radiogroup" aria-label="Produce grade">
              {GRADES.map((gradeKey) => {
                const isSelected = gradeKey === grade;
                return (
                  <button
                    key={gradeKey}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    onClick={() => setGrade(gradeKey)}
                    className={`px-2 py-2.5 rounded-xl text-xs font-black border transition-colors ${
                      isSelected
                        ? 'bg-emerald-700 text-white border-emerald-700 shadow-sm'
                        : 'bg-white text-slate-700 border-slate-200 hover:bg-emerald-50'
                    }`}
                  >
                    Grade {gradeKey}
                  </button>
                );
              })}
            </div>
          </div>

        </div>
      </div>

      {/* Grade-wise Price Cards */}
      <div className="bg-white rounded-3xl p-5 sm:p-6 border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-extrabold text-slate-900 tracking-tight">
              Grade-wise Price Estimates
            </h3>
            <p className="text-xs text-slate-500 font-medium">
              Expected ₹/kg for each grade of {commodity || 'produce'} in {district || 'the selected district'}
            </p>
          </div>
          {selectedGradePrice && (
            <span className="text-[11px] font-bold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
              Grade {grade}: ₹{displayPrice(selectedGradePrice.low)} – ₹{displayPrice(selectedGradePrice.high)}/kg
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {GRADES.map((gradeKey) => {
            const price = gradePrices?.[gradeKey];
            const isSelected = gradeKey === grade;
            return (
              <button
                key={gradeKey}
                type="button"
                onClick={() => setGrade(gradeKey)}
                className={`text-center rounded-3xl p-5 border-2 transition-colors ${
                  isSelected
                    ? 'bg-gradient-to-b from-emerald-50 to-white border-emerald-400 shadow-sm'
                    : 'bg-white border-slate-200/80 hover:border-emerald-200'
                }`}
              >
                <span className={`text-xs font-black uppercase tracking-wider block ${isSelected ? 'text-emerald-900' : 'text-slate-500'}`}>
                  Grade {gradeKey} · {gradeLabel[gradeKey]}
                </span>
                <div className={`font-black font-['Space_Grotesk'] mt-1 ${isSelected ? 'text-4xl text-emerald-800' : 'text-3xl text-slate-900'}`}>
                  ₹{displayPrice(price?.typical)}
                  <span className="text-xs font-bold text-slate-400 font-sans">/kg</span>
                </div>
                <p className={`text-[11px] font-semibold mt-1 ${isSelected ? 'text-emerald-700' : 'text-slate-400'}`}>
                  Range ₹{displayPrice(price?.low)} – ₹{displayPrice(price?.high)}/kg
                </p>
              </button>
            );
          })}
        </div>

        <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-100 font-medium">
          {currentMarketData?.gradeBasis || 'Grade prices are estimated from the reported mandi price spread.'}
        </p>
      </div>

      {/* 3 Reported Price Cards */}
      <h3 className="text-sm font-extrabold text-slate-700 tracking-tight">
        Reported Mandi Benchmark (all grades)
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 !mt-3">
        {/* Min Price */}
        <div className="bg-white rounded-3xl p-5 border border-slate-200/80 shadow-xs text-center">
          <span className="text-xs font-extrabold text-slate-500 uppercase tracking-wider block">
            Minimum Reported Price
          </span>
          <div className="text-3xl font-black text-slate-900 font-['Space_Grotesk'] mt-1">
            ₹{displayPrice(summary?.min)}
            <span className="text-xs font-bold text-slate-400 font-sans">/kg</span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium mt-1">
            Lowest reported mandi rate
          </p>
        </div>

        {/* Modal Price */}
        <div className="bg-gradient-to-b from-emerald-50 to-white rounded-3xl p-5 border-2 border-emerald-400 shadow-sm text-center relative">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-700 text-white text-[10px] font-black uppercase tracking-wider px-3 py-0.5 rounded-full shadow-xs">
            District Average
          </div>
          <span className="text-xs font-black text-emerald-900 uppercase tracking-wider block">
            Average Modal Price
          </span>
          <div className="text-4xl font-black text-emerald-800 font-['Space_Grotesk'] mt-1">
            ₹{displayPrice(summary?.modal)}
            <span className="text-sm font-bold text-emerald-600 font-sans">/kg</span>
          </div>
          <p className="text-[11px] text-emerald-700 font-semibold mt-1">
            Average of reported market modal rates
          </p>
        </div>

        {/* Max Price */}
        <div className="bg-white rounded-3xl p-5 border border-slate-200/80 shadow-xs text-center">
          <span className="text-xs font-extrabold text-slate-500 uppercase tracking-wider block">
            Maximum Reported Price
          </span>
          <div className="text-3xl font-black text-emerald-950 font-['Space_Grotesk'] mt-1">
            ₹{displayPrice(summary?.max)}
            <span className="text-xs font-bold text-slate-400 font-sans">/kg</span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium mt-1">
            Highest reported mandi rate
          </p>
        </div>
      </div>

      {/* 2-Column Responsive Body Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* ======================================================== */}
        {/* LEFT COLUMN: Market Comparison Table & Yards             */}
        {/* ======================================================== */}
        <div className="lg:col-span-12 space-y-5">
          <div className="bg-white rounded-3xl p-5 sm:p-6 border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-extrabold text-slate-900 tracking-tight">
                  APMC Mandi Yards Comparison
                </h3>
                <p className="text-xs text-slate-500 font-medium">
                  Latest reported rates for {commodity} in {district}
                </p>
              </div>
              <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                Daily reported data
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 text-[11px] font-extrabold text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-3">Mandi Yard</th>
                    <th className="py-3 px-2 text-center">Min (₹/kg)</th>
                    <th className="py-3 px-2 text-center">Modal (₹/kg)</th>
                    <th className="py-3 px-2 text-center">Max (₹/kg)</th>
                    <th className="py-3 px-2 text-center text-emerald-700">Grade {grade} (₹/kg)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs font-semibold text-slate-800">
                  {comparisons.length === 0 && (
                    <tr>
                      <td colSpan="5" className="py-6 text-center text-slate-500">
                        No market records are available for this selection.
                      </td>
                    </tr>
                  )}
                  {comparisons.map((row) => {
                    const isBest = row.isBest;
                    return (
                      <tr
                        key={row.name}
                        className={`transition-colors ${
                          isBest
                            ? 'bg-emerald-50/70 font-bold text-emerald-950'
                            : 'hover:bg-slate-50'
                        }`}
                      >
                        <td className="py-3.5 px-3">
                          <div className="flex items-center gap-2">
                            <span>{row.name}</span>
                            {isBest && (
                              <span className="text-[10px] bg-emerald-700 text-white px-2 py-0.5 rounded-full font-black">
                                Highest Modal
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-2 text-center text-slate-600">₹{displayPrice(row.min)}</td>
                        <td className="py-3.5 px-2 text-center font-black text-emerald-800 text-sm font-['Space_Grotesk']">
                          ₹{displayPrice(row.modal)}
                        </td>
                        <td className="py-3.5 px-2 text-center text-slate-600">₹{displayPrice(row.max)}</td>
                        <td className="py-3.5 px-2 text-center font-black text-emerald-700 text-sm font-['Space_Grotesk']">
                          ₹{displayPrice(row.gradePrices?.[grade]?.typical)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-100 font-medium">
              *Source prices are per quintal and converted to ₹/kg. The district modal value is an unweighted average of reported market modal prices. Grade A/B/C prices are estimates derived from each market's reported min–modal–max spread; distance is not provided.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default MarketPricePage;
