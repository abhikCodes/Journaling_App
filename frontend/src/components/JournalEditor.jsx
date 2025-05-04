import React, { useState, useEffect, useRef } from 'react'
import { format } from 'date-fns'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { journalApi } from '../api'

const JournalEditor = ({ entry, onSaved }) => {
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isGeneratingTitle, setIsGeneratingTitle] = useState(false)
  const [isGeneratingCover, setIsGeneratingCover] = useState(false)
  const [errors, setErrors] = useState({})
  const [image, setImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const fileInputRef = useRef(null)
  const contentAreaRef = useRef(null)

  // Get today's date for max date constraint
  const today = format(new Date(), 'yyyy-MM-dd')

  // Common tags for quick selection
  const quickTags = ['happy', 'inspired', 'tired', 'anxious', 'grateful', 'productive']

  useEffect(() => {
    if (entry) {
      setDate(format(new Date(entry.date), 'yyyy-MM-dd'))
      setTitle(entry.title || '')
      setContent(entry.content)
      setTags(entry.tags || [])
      
      // Set image if it exists in the entry
      if (entry.image_url) {
        setImagePreview(entry.image_url)
        setImage(null) // We don't need to re-upload existing images
      } else {
        setImagePreview(null)
        setImage(null)
      }
    } else {
      setDate(format(new Date(), 'yyyy-MM-dd'))
      setTitle('')
      setContent('')
      setTags([])
      setImagePreview(null)
      setImage(null)
    }
    // Clear any previous errors when entry changes
    setErrors({})
  }, [entry])

  const handleImageChange = (e) => {
    const file = e.target.files[0]
    if (!file) return

    // Check file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please upload an image file')
      return
    }

    // Check file size (limit to 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image size should be less than 5MB')
      return
    }

    setImage(file)
    
    // Create a preview
    const reader = new FileReader()
    reader.onload = () => {
      setImagePreview(reader.result)
    }
    reader.readAsDataURL(file)
  }

  const handleRemoveImage = () => {
    setImage(null)
    setImagePreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleSave = async () => {
    // Clear previous errors
    setErrors({})

    if (!content.trim()) {
      toast.error('Please add some content to your journal entry')
      return
    }

    try {
      setIsSaving(true)
      
      // Create FormData for file upload
      const formData = new FormData()
      formData.append('date', date)
      formData.append('content', content)
      if (title.trim()) {
        formData.append('title', title.trim())
      }
      
      // Convert tags array to JSON string for the backend
      formData.append('tags', JSON.stringify(tags))
      
      // Only append image if a new one is selected
      if (image) {
        formData.append('image', image)
      }

      let response;
      if (entry?.id) {
        // Update existing entry
        response = await journalApi.updateEntry(entry.id, formData)
        toast.success('Journal entry updated!')
      } else {
        // Create new entry
        response = await journalApi.createEntry(formData)
        toast.success('New journal entry created!')
      }

      onSaved()
    } catch (error) {
      console.error('Error saving journal entry:', error)
      
      // Handle backend validation errors
      if (error.status === 400 || error.status === 422) {
        // Display the specific error message from the backend
        toast.error(error.message)
        
        // If validation errors exist, set them in state
        if (error.data && typeof error.data === 'object') {
          setErrors(error.data)
        }
      } else {
        toast.error('Failed to save journal entry')
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!entry?.id) return
    
    try {
      setIsDeleting(true)
      await journalApi.deleteEntry(entry.id)
      toast.success('Journal entry deleted')
      onSaved()
    } catch (error) {
      console.error('Error deleting entry:', error)
      toast.error('Failed to delete entry')
    } finally {
      setIsDeleting(false)
    }
  }

  const addTag = (tag) => {
    tag = tag.trim().toLowerCase()
    if (tag && !tags.includes(tag) && tags.length < 5) {
      setTags([...tags, tag])
      setTagInput('')
    } else if (tags.length >= 5) {
      toast.error('Maximum 5 tags allowed', { icon: '⚠️' })
    }
  }

  const removeTag = (tagToRemove) => {
    setTags(tags.filter(tag => tag !== tagToRemove))
  }

  const handleTagInputKeyDown = (e) => {
    if (e.key === 'Enter' && tagInput) {
      e.preventDefault()
      addTag(tagInput)
    }
  }

  const generateFriendsStyleTitle = async () => {
    // Minimum word count threshold
    const MIN_WORDS = 20;
    const wordCount = content.trim().split(/\s+/).length;
    
    console.log("Generate title clicked, content length:", content.length);
    console.log("Word count:", wordCount);

    if (wordCount < MIN_WORDS) {
      console.log("Not enough words, minimum required:", MIN_WORDS);
      toast.error(`Your journal needs at least ${MIN_WORDS} words to generate a title (current: ${wordCount})`, {
        duration: 4000,
        icon: '📝'
      });
      return;
    }

    try {
      console.log("Making API request to generate title...");
      setIsGeneratingTitle(true);
      const response = await journalApi.generateTitle(content);
      console.log("Title generated:", response.data.title);
      setTitle(response.data.title);
      toast.success('Title generated in Friends style!', { icon: '🎬' });
    } catch (error) {
      console.error('Error generating title:', error);
      if (error.response?.data?.detail) {
        console.log("Error details:", error.response.data.detail);
        toast.error(error.response.data.detail);
      } else {
        toast.error('Failed to generate title');
      }
    } finally {
      setIsGeneratingTitle(false);
    }
  };

  const generateAICover = async () => {
    // Minimum word count threshold
    const MIN_WORDS = 20;
    const wordCount = content.trim().split(/\s+/).length;
    
    if (wordCount < MIN_WORDS) {
      toast.error(`Your journal needs at least ${MIN_WORDS} words to generate a cover image (current: ${wordCount})`, {
        duration: 4000,
        icon: '📝'
      });
      return;
    }

    try {
      setIsGeneratingCover(true);
      toast.info('Generating AI cover image...', { 
        id: 'generating-cover',
        duration: 60000 // Long duration as image generation can take time
      });
      
      const response = await journalApi.generateCoverImage(content, title);
      
      // Update the image preview with the generated image
      setImagePreview(response.data.image_url);
      setImage(null); // Clear any existing file upload
      
      toast.dismiss('generating-cover');
      toast.success('AI cover image generated!', { icon: '🎨' });
    } catch (error) {
      console.error('Error generating cover image:', error);
      toast.dismiss('generating-cover');
      if (error.data?.detail) {
        toast.error(error.data.detail);
      } else {
        toast.error('Failed to generate cover image. Please try again.');
      }
    } finally {
      setIsGeneratingCover(false);
    }
  };

  if (!entry) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-midnight/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-midnight" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </div>
          <h3 className="text-xl font-bold mb-2">No Entry Selected</h3>
          <p className="text-text-light">Select an entry from the list or create a new one.</p>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="h-full flex flex-col"
    >
      {/* Header with date and image controls */}
      <div className="bg-white rounded-lg shadow-sm p-3 mb-3">
        <div className="flex justify-between items-center">
          {/* Date picker */}
          <div className="relative">
            <div className="flex items-center">
              <svg className="w-4 h-4 text-gray-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                max={today}
                className="input px-2 py-1 text-sm focus:border-primary focus:ring-1 focus:ring-primary/20 border-gray-200"
              />
            </div>
            {errors.date && (
              <p className="text-red-500 text-xs mt-1">{errors.date}</p>
            )}
          </div>
          
          {/* Image buttons */}
          <div className="flex items-center gap-2">
            {/* AI Image Generation Button */}
            <button 
              className="btn-secondary px-3 py-1.5 rounded-md text-white flex items-center gap-1 text-xs shadow-sm hover:shadow transition-all"
              title="Generate AI cover image"
              onClick={generateAICover}
              disabled={isGeneratingCover || !content.trim() || content.trim().split(/\s+/).length < 20}
            >
              {isGeneratingCover ? (
                <>
                  <svg className="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 3H12H8C6.34315 3 5 4.34315 5 6V18C5 19.6569 6.34315 21 8 21H16C17.6569 21 19 19.6569 19 18V8.625M13.5 3L19 8.625M13.5 3V8.625H19" />
                  </svg>
                  <span>AI Cover</span>
                </>
              )}
            </button>

            {/* Upload or Preview */}
            {imagePreview ? (
              <div className="relative">
                <img 
                  src={imagePreview} 
                  alt="Preview" 
                  className="w-8 h-8 rounded-md object-cover border border-gray-200" 
                />
                <button 
                  className="absolute -top-1.5 -right-1.5 bg-red-500 text-white p-0.5 rounded-full hover:bg-red-600 w-4 h-4 flex items-center justify-center shadow-sm"
                  onClick={handleRemoveImage}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <label className="btn-ghost px-3 py-1.5 rounded-md text-gray-500 hover:text-primary border border-gray-200 hover:border-primary/50 cursor-pointer flex items-center gap-1 text-xs">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>Add Image</span>
                <input 
                  type="file" 
                  className="hidden" 
                  accept="image/*"
                  onChange={handleImageChange}
                  ref={fileInputRef}
                />
              </label>
            )}
          </div>
        </div>
      </div>

      {/* Title input with tags section */}
      <div className="bg-white rounded-lg shadow-sm p-3 mb-3">
        {/* Title input with magic wand button */}
        <div className="relative mb-3">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Entry title (optional)"
            className="input py-2 px-3 w-full text-lg font-medium pr-12 border-gray-200 focus:border-primary focus:ring-1"
            maxLength={100}
          />
          {errors.title && (
            <p className="text-red-500 text-xs mt-1">{errors.title}</p>
          )}
          
          {/* Magic wand title generator button */}
          <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
            <div className="relative group">
              <button
                type="button"
                onClick={() => {
                  console.log("Button clicked");
                  generateFriendsStyleTitle();
                }}
                disabled={isGeneratingTitle || !content.trim()}
                className="bg-primary/10 hover:bg-primary/20 transition-colors rounded-full p-2 text-primary"
                aria-label="Generate Friends-style title"
              >
                {isGeneratingTitle ? (
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                )}
              </button>
              <div className="absolute pointer-events-none bottom-full right-0 mb-2 w-48 rounded bg-gray-800 p-2 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
                Generate Friends style title
              </div>
            </div>
          </div>
        </div>
        
        {/* Tag section */}
        <div className="flex gap-2 items-center mb-2">
          <div className="relative flex-1 max-w-[200px]">
            <input
              type="text"
              placeholder="Add tag..."
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagInputKeyDown}
              className="input py-1 px-2 pr-8 text-sm w-full border-gray-200 focus:border-primary focus:ring-1"
              maxLength={15}
            />
            {tagInput && (
              <button
                onClick={() => addTag(tagInput)}
                className="absolute right-1 top-1/2 transform -translate-y-1/2 text-primary"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            )}
          </div>
          
          {/* Quick tags in a cleaner row */}
          {tags.length < 5 && (
            <div className="flex flex-wrap gap-1.5 flex-1">
              {quickTags
                .filter(tag => !tags.includes(tag))
                .slice(0, 5 - tags.length)
                .map(tag => (
                  <button
                    key={tag}
                    onClick={() => addTag(tag)}
                    className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-text hover:bg-gray-200 transition-colors"
                  >
                    + {tag}
                  </button>
                ))
              }
            </div>
          )}
        </div>
        
        {/* Tag display */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tags.map(tag => (
              <div key={tag} className="bg-primary/10 rounded-full px-2 py-0.5 flex items-center gap-1 text-xs">
                <span>{tag}</span>
                <button onClick={() => removeTag(tag)} className="text-text-light hover:text-accent">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Content textarea with floating image if present */}
      <div className="flex-1 bg-white rounded-lg shadow-sm p-3 mb-3 relative" ref={contentAreaRef}>
        {imagePreview && (
          <div className="absolute top-2 right-2 z-10 w-1/4 max-w-[180px]">
            <div className="relative rounded-md overflow-hidden shadow-md">
              <img 
                src={imagePreview} 
                alt="Journal entry" 
                className="w-full h-auto object-cover" 
              />
              <button 
                className="absolute top-1 right-1 bg-red-500 text-white p-1 rounded-full hover:bg-red-600 shadow-md"
                onClick={handleRemoveImage}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        )}
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write your journal entry here..."
          className={`h-full w-full border-0 p-0 focus:ring-0 resize-none ${imagePreview ? 'pr-[calc(25%+16px)]' : ''}`}
        ></textarea>
        {errors.content && (
          <p className="text-red-500 text-xs mt-1">{errors.content}</p>
        )}
      </div>

      {/* Footer with word count and action buttons */}
      <div className="bg-white rounded-lg shadow-sm p-3">
        {/* Word count indicator */}
        <div className="text-xs text-text-light mb-2">
          {content.trim().split(/\s+/).length} words
          {content.trim().split(/\s+/).length < 20 && (
            <span className="text-red-500 ml-1">
              (minimum 20 words required)
            </span>
          )}
        </div>
        
        {/* Action buttons */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleSave}
            disabled={isSaving || isDeleting}
            className="btn-primary px-4 py-2 rounded-md text-white shadow-sm hover:shadow transition-all"
          >
            {isSaving ? 'Saving...' : entry.id ? 'Update Entry' : 'Save Entry'}
          </button>
          
          {entry.id ? (
            <button
              onClick={handleDelete}
              disabled={isDeleting || isSaving}
              className="btn-outline-accent px-4 py-2 rounded-md text-accent border border-accent hover:bg-accent hover:text-white transition-colors"
            >
              {isDeleting ? 'Deleting...' : 'Delete Entry'}
            </button>
          ) : (
            <div></div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export default JournalEditor