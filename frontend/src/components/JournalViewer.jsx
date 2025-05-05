import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { format } from 'date-fns';

const JournalViewer = ({ entry, onEdit, onNavigate, hasMultipleEntries }) => {
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [currentEntry, setCurrentEntry] = useState(entry);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const prevEntryRef = useRef(entry);
  const [imageLoadError, setImageLoadError] = useState({});
  
  // Update currentEntry when entry changes from parent, except during transitions
  useEffect(() => {
    if (!isTransitioning) {
      setCurrentEntry(entry);
      prevEntryRef.current = entry;
    }
  }, [entry, isTransitioning]);
  
  if (!entry) {
    return null;
  }

  // Pre-check image validity and update state
  useEffect(() => {
    // Skip during transitions to avoid unnecessary requests
    if (isTransitioning) return;

    // If there's an image, try to preload it
    if (entry.image_url && !imageLoadError[entry.id]) {
      const img = new Image();
      img.onload = () => {
        // Image loaded successfully
        setImageLoadError(prev => ({...prev, [entry.id]: false}));
      };
      img.onerror = () => {
        // Image failed to load, mark it as failed
        console.error("Failed to preload image:", entry.image_url);
        setImageLoadError(prev => ({...prev, [entry.id]: true}));
      };
      
      // Add cache-busting parameter and attempt to load
      img.src = `${entry.image_url}?v=${Date.now()}`;
    }
  }, [entry.id, entry.image_url, isTransitioning]);

  // Custom navigation function that maintains fullscreen state
  const handleNavigate = (direction) => {
    // Prevent multiple rapid transitions
    if (isTransitioning) return;
    
    // Set transitioning state to prevent flicker
    setIsTransitioning(true);
    
    // Store current entry before navigation
    prevEntryRef.current = currentEntry;
    
    // Call the parent's navigate function immediately to start loading the next entry
    onNavigate(direction);
    
    // Reset transitioning state after a delay to allow smooth transition
    setTimeout(() => {
      setIsTransitioning(false);
    }, 300);
  };

  const formatDate = (dateString) => {
    return format(new Date(dateString), 'EEEE, MMMM do yyyy');
  };

  // Get tag colors based on tag name
  const getTagColor = (tag) => {
    const colors = {
      'happy': 'bg-secondary/20 text-text-dark',
      'sad': 'bg-accent/20 text-text-dark',
      'work': 'bg-primary/20 text-text-dark',
      'family': 'bg-midnight/20 text-text-dark',
      'inspired': 'bg-emerald-100 text-emerald-800',
      'tired': 'bg-gray-100 text-gray-800',
      'anxious': 'bg-red-100 text-red-800',
      'grateful': 'bg-indigo-100 text-indigo-800',
      'productive': 'bg-blue-100 text-blue-800',
    };
    
    // Default color for unknown tags
    return colors[tag.toLowerCase()] || 'bg-gray-200 text-text-dark';
  };

  // Use the entry that's currently being displayed
  const displayEntry = isTransitioning ? prevEntryRef.current : currentEntry;

  // Function to ensure image URL works correctly in Docker environment
  const getImageUrl = (url) => {
    if (!url) return null;
    
    // If it's already a relative URL or starts with http and doesn't contain backend:8000
    if (url.startsWith('/') || (url.startsWith('http') && !url.includes('backend:8000'))) {
      return url;
    }
    
    // Handle Docker backend URLs by converting to relative URLs for proxy
    if (url.includes('backend:8000')) {
      // Extract the path part after backend:8000
      const pathMatch = url.match(/backend:8000(\/.*)/);
      if (pathMatch && pathMatch[1]) {
        return pathMatch[1]; // Return just the path part which will use the proxy
      }
    }
    
    // Default fallback
    return url;
  };

  // Check if we should show the image for this entry
  const shouldShowImage = (entryId) => {
    return entryId && 
           displayEntry.image_url && 
           imageLoadError[entryId] !== true;
  };

  // Fullscreen journal entry content
  const FullscreenJournalContent = ({ entry }) => (
    <motion.div 
      className="bg-white rounded-xl shadow-lg p-6 my-4 relative overflow-hidden flex-grow"
      key={`fullscreen-content-${entry.id || 'new'}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-secondary to-accent"></div>
      
      <div className="relative">
        {/* Title */}
        {entry.title && (
          <div className="mb-6">
            <h1 
              className="text-3xl md:text-4xl font-bold text-midnight-dark leading-tight"
              style={{
                fontFamily: "'Playfair Display', serif",
                fontWeight: 700,
                letterSpacing: "-0.02em"
              }}
            >
              {entry.title}
            </h1>
          </div>
        )}
      
        {/* Image floated to allow text wrapping */}
        {shouldShowImage(entry.id) && (
          <div className="float-right ml-6 mb-4 w-full sm:w-1/3 md:w-1/3 lg:w-1/4">
            <img 
              src={getImageUrl(entry.image_url)}
              alt="Journal entry" 
              className="w-full rounded-lg object-cover" 
              onError={() => {
                setImageLoadError(prev => ({...prev, [entry.id]: true}));
              }}
            />
          </div>
        )}
      
        {/* Content with clean styling - now will wrap around the image */}
        <div className="prose prose-lg max-w-none text-slate-700 clearfix">
          {entry.content.split('\n').map((paragraph, index) => (
            paragraph ? (
              <p key={index} className="mb-4 leading-relaxed">
                {paragraph}
              </p>
            ) : <br key={index} />
          ))}
        </div>
      
        {/* Clear the float after content */}
        <div className="clear-both"></div>
      </div>
    </motion.div>
  );

  // Full screen content component - stays mounted during navigation
  const FullScreenContent = () => (
    <div className="fixed inset-0 bg-background z-50 overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto h-full flex flex-col relative">
        {/* Exit button */}
        <motion.button
          onClick={() => setIsFullScreen(false)}
          className="absolute top-0 right-0 p-2 rounded-full bg-white/80 text-text-dark z-10 hover:bg-white transition-colors shadow-md"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </motion.button>
        
        <div className="my-4 text-text-light text-sm font-medium italic">
          {formatDate(displayEntry.date)}
        </div>
        
        {/* AnimatePresence to handle content transitions */}
        <AnimatePresence mode="wait">
          <FullscreenJournalContent entry={displayEntry} key={`fullscreen-${displayEntry.id || 'new'}`} />
        </AnimatePresence>
        
        {/* Navigation arrows - enlarged for full screen */}
        {hasMultipleEntries && (
          <div className="flex justify-between py-4">
            <motion.button
              onClick={() => handleNavigate('prev')}
              className="p-3 rounded-full bg-white shadow-md text-gray-600 hover:bg-primary/10 hover:text-primary transition-colors"
              aria-label="Previous entry"
              whileHover={{ x: -5, scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              disabled={isTransitioning}
            >
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </motion.button>
            <motion.button
              onClick={() => handleNavigate('next')}
              className="p-3 rounded-full bg-white shadow-md text-gray-600 hover:bg-primary/10 hover:text-primary transition-colors"
              aria-label="Next entry"
              whileHover={{ x: 5, scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              disabled={isTransitioning}
            >
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </motion.button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* FullScreenContent only gets mounted/unmounted when toggling fullscreen */}
      {isFullScreen && <FullScreenContent />}
      
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="h-full flex flex-col max-w-4xl mx-auto"
      >
        <div className="flex justify-between items-center mb-6">
          <div className="text-text-light text-sm font-medium italic">
            {formatDate(displayEntry.date)}
          </div>
          <div className="flex gap-2">
            <motion.button
              onClick={() => setIsFullScreen(true)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-white text-midnight-dark shadow-sm border border-gray-100 hover:bg-gray-50 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              title="Full Screen"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5" />
              </svg>
              <span className="text-xs font-medium">Fullscreen</span>
            </motion.button>
            <motion.button
              onClick={onEdit}
              className="btn btn-primary btn-sm"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Edit
            </motion.button>
          </div>
        </div>

        <motion.div 
          className="bg-white rounded-xl shadow-lg p-6 mb-6 relative overflow-hidden"
          key={`regular-${displayEntry.id || 'new'}`}
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.4 }}
        >
          {/* Clean, minimal accent line */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-secondary to-accent"></div>
          
          <div className="relative">
            {/* Title with Gen Z friendly styling */}
            {displayEntry.title && (
              <div className="mb-6">
                <motion.h1 
                  className="text-3xl md:text-4xl font-bold text-midnight-dark leading-tight"
                  style={{
                    fontFamily: "'Playfair Display', serif",
                    fontWeight: 700,
                    letterSpacing: "-0.02em"
                  }}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2, duration: 0.5 }}
                >
                  {displayEntry.title}
                </motion.h1>
              </div>
            )}
            
            {/* Tags with clean styling */}
            {displayEntry.tags && displayEntry.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-6">
                {displayEntry.tags.map(tag => (
                  <motion.span 
                    key={tag} 
                    className={`text-xs px-3 py-1 rounded-full ${getTagColor(tag)}`}
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.3 }}
                    whileHover={{ scale: 1.05 }}
                  >
                    {tag}
                  </motion.span>
                ))}
              </div>
            )}
            
            {/* Image floated to allow text wrapping */}
            {shouldShowImage(displayEntry.id) && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3, duration: 0.5 }}
                className="float-right ml-6 mb-4 w-full sm:w-1/3 md:w-1/3 lg:w-1/4"
                whileHover={{ scale: 1.02 }}
              >
                <img 
                  src={getImageUrl(displayEntry.image_url)}
                  alt="Journal entry" 
                  className="w-full rounded-lg object-cover" 
                  onError={() => {
                    setImageLoadError(prev => ({...prev, [displayEntry.id]: true}));
                  }}
                />
              </motion.div>
            )}
            
            {/* Content with clean styling - now will wrap around the image */}
            <div className="prose prose-lg max-w-none text-slate-700 clearfix">
              {displayEntry.content.split('\n').map((paragraph, index) => (
                paragraph ? (
                  <p key={index} className="mb-4 leading-relaxed">
                    {paragraph}
                  </p>
                ) : <br key={index} />
              ))}
            </div>
            
            {/* Clear the float after content */}
            <div className="clear-both"></div>
            
            {/* Emotion indicator with minimalist styling */}
            {displayEntry.emotion_tags && displayEntry.emotion_tags.length > 0 && (
              <div className="mt-8 pt-4 border-t border-gray-100">
                <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Emotions</p>
                <div className="flex flex-wrap gap-2">
                  {displayEntry.emotion_tags.map(emotion => (
                    <span 
                      key={emotion} 
                      className="text-xs px-3 py-1 rounded-full bg-gray-100 text-text-dark"
                    >
                      {emotion}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </motion.div>
        
        {/* Navigation arrows with minimalist styling */}
        {hasMultipleEntries && (
          <div className="flex justify-between mt-auto">
            <motion.button
              onClick={() => onNavigate('prev')}
              className="p-2 rounded-full bg-gray-100 text-gray-600 hover:bg-primary/10 hover:text-primary transition-colors"
              aria-label="Previous entry"
              whileHover={{ x: -3, scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </motion.button>
            <motion.button
              onClick={() => onNavigate('next')}
              className="p-2 rounded-full bg-gray-100 text-gray-600 hover:bg-primary/10 hover:text-primary transition-colors"
              aria-label="Next entry"
              whileHover={{ x: 3, scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </motion.button>
          </div>
        )}
      </motion.div>
    </>
  );
};

export default JournalViewer; 