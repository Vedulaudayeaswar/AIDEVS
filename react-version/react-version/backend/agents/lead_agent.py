"""Engineering Lead Agent - Orchestrates the workflow"""
from .base_agent import BaseAgent

class LeadAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Engineering Lead",
            role="orchestrator",
            system_prompt="""You are a friendly, helpful web development assistant. Your role is to:
1. Have natural conversations with users about building their website
2. Ask clarifying questions to understand their needs
3. Provide helpful suggestions and examples
4. Guide them through each section (header, hero, features, footer)
5. Be encouraging and supportive throughout the process

Current conversation stage will be provided. Adapt your responses accordingly.
Keep responses conversational, concise, and actionable."""
        )
        self.current_stage = "initial"
        self.gathered_info = {}
        self.waiting_for_section = None  # Track which section we're waiting to build
        self.conversation_history = []  # Track conversation for context
    
    def _generate_contextual_response(self, user_message, stage_context, api_key):
        """Use LLM to generate contextual, helpful responses"""
        # Build context message
        context = f"""
**Current Stage**: {self.current_stage}
**Gathered Info**: {self.gathered_info}
**Stage Context**: {stage_context}
**User Message**: {user_message}

Generate a helpful, conversational response that:
1. Acknowledges what the user said
2. Provides relevant suggestions or examples based on their website type
3. Guides them on what to do next
4. Keeps it friendly and encouraging (2-3 sentences max)
"""
        
        # Add conversation history for context
        messages = self.conversation_history[-4:] if self.conversation_history else []
        messages.append({"role": "user", "content": context})
        
        # Generate response using the model
        response = self.generate_response(context, api_key=api_key)
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def process_request(self, user_message, rag_context=None, api_key=None):
        """Process user request with intelligent stage management"""
        user_lower = user_message.lower()
        
        # Initial stage - user describes what they want
        if self.current_stage == "initial":
            # Check if they mentioned website type or any website-related intent
            if any(word in user_lower for word in ['website', 'ecommerce', 'portfolio', 'blog', 'landing', 'business', 'shop', 'site', 'page', 'build', 'create', 'make']):
                self.gathered_info['type'] = user_message
                self.current_stage = "gathering_details"
                
                # Use LLM to generate contextual response
                stage_context = "User just described their website type. Ask for website name and color scheme in a friendly way. Provide 2-3 color scheme examples based on their website type."
                response = self._generate_contextual_response(user_message, stage_context, api_key)
                
                return {
                    'response': response,
                    'next_agent': 'lead',
                    'stage': 'gathering_details'
                }
            else:
                # Use LLM for initial greeting
                stage_context = "This is the first message. Greet the user warmly and ask what type of website they want to build. Give 3-4 examples (ecommerce, portfolio, food delivery, blog)."
                response = self._generate_contextual_response(user_message, stage_context, api_key)
                
                return {
                    'response': response,
                    'next_agent': 'lead',
                    'stage': 'initial'
                }
        
        # Gathering details stage
        elif self.current_stage == "gathering_details":
            self.gathered_info['details'] = user_message
            self.current_stage = "waiting_header"
            self.waiting_for_section = "header"
            
            # Use LLM to suggest header ideas based on website type
            website_type = self.gathered_info.get('type', '')
            stage_context = f"User provided website details: '{user_message}'. Their website type is: '{website_type}'. Now ask them to describe their header section. Provide 3-4 specific header suggestions tailored to their website type (logo placement, navigation items, style effects like glassmorphism)."
            response = self._generate_contextual_response(user_message, stage_context, api_key)
            
            return {
                'response': response,
                'next_agent': 'lead',
                'stage': 'waiting_header'
            }
        
        # Waiting for header instructions
        elif self.current_stage == "waiting_header":
            self.gathered_info['header_instructions'] = user_message
            self.current_stage = "header"
            self.waiting_for_section = None
            return {
                'response': f"Building header: {user_message}",
                'next_agent': 'frontend',
                'stage': 'header'
            }
        
        # Header built - ask for hero instructions
        elif self.current_stage == "header":
            self.current_stage = "waiting_hero"
            self.waiting_for_section = "hero"
            
            # Use LLM to suggest hero section ideas
            website_type = self.gathered_info.get('type', '')
            stage_context = f"The header is complete. Now ask for hero section details. Based on their '{website_type}' website, suggest 2-3 compelling hero section ideas (headline examples, subtitle, CTA button text). Make it specific to their type."
            response = self._generate_contextual_response(user_message, stage_context, api_key)
            
            return {
                'response': response,
                'next_agent': 'lead',
                'stage': 'waiting_hero'
            }
        
        # Waiting for hero instructions
        elif self.current_stage == "waiting_hero":
            # Check if user is asking for suggestions
            if any(word in user_lower for word in ['suggest', 'help', 'idea', 'what should', 'dont know', "don't know"]):
                website_type = self.gathered_info.get('type', '')
                stage_context = f"User needs hero section suggestions for their '{website_type}' website. Provide 2-3 creative hero headline options with subtitles and CTA button ideas. Be specific and inspiring."
                response = self._generate_contextual_response(user_message, stage_context, api_key)
                return {
                    'response': response,
                    'next_agent': 'lead',
                    'stage': 'waiting_hero'
                }
            else:
                # User provided hero instructions
                self.gathered_info['hero_instructions'] = user_message
                self.current_stage = "hero"
                self.waiting_for_section = None
                return {
                    'response': f"Building hero section: {user_message}",
                    'next_agent': 'frontend',
                    'stage': 'hero'
                }
        
        # Hero built - ask for features instructions
        elif self.current_stage == "hero":
            self.current_stage = "waiting_features"
            self.waiting_for_section = "features"
            
            # Use LLM to suggest features
            website_type = self.gathered_info.get('type', '')
            stage_context = f"Hero section is complete! Now ask for features/services they want to showcase. Based on their '{website_type}' website, suggest 4-5 compelling features that would resonate with their audience. Be creative and specific."
            response = self._generate_contextual_response(user_message, stage_context, api_key)
            
            return {
                'response': response,
                'next_agent': 'lead',
                'stage': 'waiting_features'
            }
        
        # Waiting for features instructions
        elif self.current_stage == "waiting_features":
            # Check if user is asking for suggestions
            if any(word in user_lower for word in ['suggest', 'help', 'idea', 'what should', 'dont know', "don't know"]):
                website_type = self.gathered_info.get('type', '')
                stage_context = f"User needs feature/service suggestions for their '{website_type}' website. Provide 4-6 specific, compelling features that would attract customers. Make them actionable and benefit-focused."
                response = self._generate_contextual_response(user_message, stage_context, api_key)
                return {
                    'response': response,
                    'next_agent': 'lead',
                    'stage': 'waiting_features'
                }
            else:
                # User provided features
                self.gathered_info['features_instructions'] = user_message
                self.current_stage = "features"
                self.waiting_for_section = None
                return {
                    'response': f"Building features section: {user_message}",
                    'next_agent': 'frontend',
                    'stage': 'features'
                }
        
        # Features built - ask what's next
        elif self.current_stage == "features":
            if any(word in user_lower for word in ['footer', 'finish', 'done', 'complete']):
                self.current_stage = "waiting_footer"
                self.waiting_for_section = "footer"
                
                # Use LLM to ask about footer with suggestions
                website_type = self.gathered_info.get('type', '')
                stage_context = f"Features are done! Now ask about the footer. For a '{website_type}' website, suggest what footer elements they might want (contact info, social links, newsletter signup, sitemap, etc.)."
                response = self._generate_contextual_response(user_message, stage_context, api_key)
                
                return {
                    'response': response,
                    'next_agent': 'lead',
                    'stage': 'waiting_footer'
                }
            elif 'more features' in user_lower or 'another feature' in user_lower or 'add feature' in user_lower:
                self.current_stage = "waiting_features"
                
                # Use LLM to ask about additional features
                stage_context = "User wants to add more features. Ask what additional features they'd like to add in an encouraging way."
                response = self._generate_contextual_response(user_message, stage_context, api_key)
                
                return {
                    'response': response,
                    'next_agent': 'lead',
                    'stage': 'waiting_features'
                }
            else:
                # Auto-ask about footer with LLM
                stage_context = "Features section is complete! Ask if they're ready for the footer in an upbeat way. Briefly mention what a footer typically includes."
                response = self._generate_contextual_response(user_message, stage_context, api_key)
                
                return {
                    'response': response,
                    'next_agent': 'lead',
                    'stage': 'features'
                }
        
        # Waiting for footer instructions
        elif self.current_stage == "waiting_footer":
            self.gathered_info['footer_instructions'] = user_message
            self.current_stage = "footer"
            self.waiting_for_section = None
            return {
                'response': f"Building footer: {user_message}",
                'next_agent': 'frontend',
                'stage': 'footer'
            }
        
        # Footer complete
        elif self.current_stage == "footer":
            self.current_stage = "complete"
            return {
                'response': "🎉 **Your website is complete!**\n\n✅ Frontend sections built\n✅ Backend API generating...\n✅ Tests running...\n\nClick **Download** to get your full-stack project with:\n- Complete HTML/CSS/JS website\n- Flask backend API\n- Test results\n- Setup instructions",
                'next_agent': 'lead',
                'stage': 'complete'
            }
        
        # Complete stage
        elif self.current_stage == "complete":
            # Check if user wants to regenerate a section
            if 'regenerate' in user_lower or 'rebuild' in user_lower or 'fix' in user_lower:
                if 'header' in user_lower:
                    self.current_stage = "waiting_header"
                    return {
                        'response': "Let's rebuild the header! Describe how you want it:",
                        'next_agent': 'lead',
                        'stage': 'waiting_header'
                    }
                elif 'hero' in user_lower:
                    self.current_stage = "waiting_hero"
                    return {
                        'response': "Let's rebuild the hero section! What should it say?",
                        'next_agent': 'lead',
                        'stage': 'waiting_hero'
                    }
                elif 'feature' in user_lower:
                    self.current_stage = "waiting_features"
                    return {
                        'response': "Let's rebuild the features section! What features should I showcase?",
                        'next_agent': 'lead',
                        'stage': 'waiting_features'
                    }
                elif 'footer' in user_lower:
                    self.current_stage = "waiting_footer"
                    return {
                        'response': "Let's rebuild the footer! What should it include?",
                        'next_agent': 'lead',
                        'stage': 'waiting_footer'
                    }
            
            return {
                'response': "Your website is ready! You can download it or start a new project by clicking Reset.\n\nTip: If any section looks wrong, say 'regenerate [section name]' (e.g., 'regenerate features')",
                'next_agent': 'lead',
                'stage': 'complete'
            }
        
        # Default fallback - should never reach here but just in case
        return {
            'response': f"I'm currently waiting for: {self.waiting_for_section or 'your input'}. What would you like to do?",
            'next_agent': 'lead',
            'stage': self.current_stage
        }
    
    def _suggest_hero_headline(self, website_type):
        """Suggest hero headline based on website type"""
        suggestions = {
            'ecommerce': 'Shop the Future with AI-Powered Recommendations',
            'portfolio': 'Creating Digital Experiences That Matter',
            'blog': 'Stories That Inspire and Inform',
            'landing': 'Transform Your Business Today',
            'business': 'Excellence in Every Service We Provide'
        }
        
        for key, value in suggestions.items():
            if key in website_type.lower():
                return value
        
        return 'Welcome to Innovation'
    
    def _suggest_features(self, website_type):
        """Suggest features based on website type"""
        suggestions = {
            'ecommerce': '🛍️ Smart Product Search\n💳 Secure Checkout\n📦 Fast Shipping',
            'portfolio': '💼 Project Showcase\n🎨 Creative Work\n📞 Easy Contact',
            'blog': '📝 Latest Articles\n💬 Comments\n🔔 Newsletter',
            'business': '⚡ Our Services\n👥 Expert Team\n📊 Results'
        }
        
        for key, value in suggestions.items():
            if key in website_type.lower():
                return value
        
        return '✨ Feature One\n🚀 Feature Two\n💡 Feature Three'
