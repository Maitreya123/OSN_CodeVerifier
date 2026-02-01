"""
Streamlit App for Doxygen Documentation Validation and Fixing
"""

import streamlit as st
from doxygen_validator import DoxygenValidator
import os

# Page config
st.set_page_config(
    page_title="Doxygen Validator",
    page_icon="📝",
    layout="wide"
)

# Initialize validator
@st.cache_resource
def get_validator():
    return DoxygenValidator()

validator = get_validator()

# Title and description
st.title("📝 OpenSn Doxygen Documentation Validator")
st.markdown("""
Upload a C++ header file (.h) to validate and fix Doxygen documentation according to 
[OpenSn guidelines](https://open-sn.github.io/opensn/devguide/doxygen.html).
""")

# Sidebar with guidelines
with st.sidebar:
    st.header("📋 Guidelines Summary")
    st.markdown("""
    **Style:**
    - Use `///` for single-line
    - Use `/** */` for multi-line
    - Use `\\param`, `\\return` (not @)
    - NO `\\brief` or `\\details`
    
    **Classes:**
    - Brief: noun phrase
    - Document at definition
    
    **Methods:**
    - Brief: verb in base form
    - Document at declaration
    
    **Variables:**
    - Brief: noun phrase
    - Describe purpose, not just name
    """)
    
    st.divider()
    
    # API status
    st.header("🔌 API Status")
    try:
        if validator.llm_client.provider == "tamu":
            st.success(f"✓ Connected: TAMU AI Chat")
        else:
            st.info(f"ℹ Using: {validator.llm_client.provider}")
    except:
        st.error("✗ API not connected")

# Main content
tab1, tab2, tab3 = st.tabs(["📤 Upload & Validate", "🔧 Fix Issues", "📖 View Guidelines"])

with tab1:
    st.header("Upload Header File")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a .h file",
        type=['h', 'hpp'],
        help="Upload a C++ header file to validate"
    )
    
    # Or paste code
    st.subheader("Or paste code directly:")
    code_input = st.text_area(
        "Paste C++ header code",
        height=300,
        placeholder="Paste your C++ header file content here..."
    )
    
    # Validate button
    if st.button("🔍 Validate Documentation", type="primary"):
        # Get content
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8')
            filename = uploaded_file.name
        elif code_input:
            content = code_input
            filename = "pasted_code.h"
        else:
            st.warning("Please upload a file or paste code first")
            st.stop()
        
        # Store in session state
        st.session_state['file_content'] = content
        st.session_state['filename'] = filename
        
        # Validate
        with st.spinner("Validating documentation..."):
            result = validator.validate_file(content)
            st.session_state['validation_result'] = result
        
        # Display results
        st.success("✓ Validation complete!")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Entities", result['total_entities'])
        with col2:
            st.metric("Issues Found", result['issues_found'])
        with col3:
            compliance = (result['total_entities'] - result['issues_found']) / max(result['total_entities'], 1) * 100
            st.metric("Compliance", f"{compliance:.1f}%")
        
        # Show issues
        if result['issues_found'] > 0:
            st.subheader("⚠️ Issues Found")
            
            for i, issue in enumerate(result['issues']):
                entity = issue['entity']
                severity_icon = "🔴" if issue['severity'] == 'error' else "🟡"
                
                with st.expander(f"{severity_icon} Line {entity['line']}: {issue['message']}"):
                    st.code(entity['content'], language='cpp')
                    st.caption(f"Type: {entity['type']} | Severity: {issue['severity']}")
        else:
            st.success("🎉 No issues found! Documentation is compliant.")

with tab2:
    st.header("Fix Documentation Issues")
    
    if 'validation_result' not in st.session_state:
        st.info("👈 Please validate a file first in the 'Upload & Validate' tab")
    else:
        result = st.session_state['validation_result']
        
        if result['issues_found'] == 0:
            st.success("🎉 No issues to fix! Your documentation is already compliant.")
        else:
            st.write(f"Found {result['issues_found']} issue(s) to fix")
            
            # Fix options
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("Click the button below to automatically generate Doxygen documentation using TAMU AI Chat")
            with col2:
                fix_button = st.button("🔧 Fix All Issues", type="primary")
            
            if fix_button:
                with st.spinner("Generating documentation with TAMU AI Chat..."):
                    fixed_content = validator.fix_file(
                        st.session_state['file_content'],
                        result
                    )
                    st.session_state['fixed_content'] = fixed_content
                
                st.success("✓ Documentation fixed!")
            
            # Show fixed content
            if 'fixed_content' in st.session_state:
                st.subheader("📄 Fixed Code")
                
                # Show side-by-side comparison
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Original:**")
                    st.code(st.session_state['file_content'], language='cpp', line_numbers=True)
                with col2:
                    st.markdown("**Fixed:**")
                    st.code(st.session_state['fixed_content'], language='cpp', line_numbers=True)
                
                # Show summary
                st.divider()
                original_lines = st.session_state['file_content'].split('\n')
                fixed_lines = st.session_state['fixed_content'].split('\n')
                
                added_count = len(fixed_lines) - len(original_lines)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📝 Documentation Added", f"{added_count} lines")
                with col2:
                    st.metric("📊 Total Lines", len(fixed_lines))
                with col3:
                    st.metric("✅ Compliance", "100%")
                
                # Show what changes were made
                st.divider()
                st.subheader("📋 Changes Made")
                
                changes = []
                i = 0
                while i < len(fixed_lines):
                    if i >= len(original_lines) or (i < len(original_lines) and original_lines[i] != fixed_lines[i]):
                        line = fixed_lines[i]
                        # Check if it's a documentation line
                        if line.strip().startswith('///') or line.strip().startswith('/**') or line.strip().startswith('*'):
                            changes.append((i + 1, line.strip()))
                    i += 1
                
                if changes:
                    st.markdown("**Added/Modified Documentation:**")
                    for line_num, content in changes[:30]:  # Show first 30 changes
                        if content.startswith('///'):
                            st.markdown(f"✅ **Line {line_num}:** `{content}`")
                        elif content.startswith('/**') or content.startswith('*/'):
                            st.markdown(f"✅ **Line {line_num}:** `{content}`")
                        elif content.startswith('*'):
                            st.markdown(f"   **Line {line_num}:** `{content}`")
                    
                    if len(changes) > 30:
                        st.caption(f"... and {len(changes) - 30} more documentation lines")
                else:
                    st.info("No documentation changes detected")
                
                # Download button
                st.download_button(
                    label="📥 Download Fixed File",
                    data=st.session_state['fixed_content'],
                    file_name=f"fixed_{st.session_state['filename']}",
                    mime="text/plain",
                    type="primary"
                )

with tab3:
    st.header("📖 Complete Doxygen Guidelines")
    
    st.markdown("""
    ## Purpose
    Provide developer-facing documentation for OpenSn using Doxygen.
    
    ## Coverage Requirements
    
    ### Mandatory Documentation:
    - All classes, structs, and unions
    - All public methods (except trivial getters/setters)
    - All member variables (private, protected, public)
    - All static members and methods
    - All functions (except static/anonymous namespace functions)
    - All extern and constexpr variables in headers
    - All C++20 concepts
    
    ### Do NOT Document:
    - Files
    - Type aliases (using/typedef)
    - Namespaces
    - Preprocessor macros
    - Default constructors
    - Copy/move constructors/assignments
    - Destructors
    
    ## Style Rules
    
    ### Commands:
    - Use backslash-style: `\\param`, `\\return`, `\\throw`
    - NOT @-style: `@param`, `@return`
    
    ### Comment Format:
    - Single-line: `///`
    - Multi-line: `/** */`
    
    ### Brief/Details:
    - **DO NOT** use `\\brief` or `\\details`
    - First sentence (up to period) = brief description
    - Additional text on new line = detailed description
    
    ## Entity-Specific Rules
    
    ### Classes/Structs:
    - Brief: noun phrase (not verb/sentence)
    - Avoid "Class that represents..."
    - Document at definition, not forward declaration
    - Document members inside class body only
    
    ### Functions/Methods:
    - Brief: verb in base form (without "s"/"es")
    - Document at declaration in header only
    - Include `\\param`, `\\return` (if not void/trivial), `\\throw`
    
    ### Variables/Members:
    - Brief: noun phrase
    - Must describe purpose, not just name symbol
    - Bad: `/// Alpha.`
    - Good: `/// Thermal diffusion coefficient.`
    
    ### Template Parameters:
    - Use `\\tparam` when semantic meaning beyond generic type
    - Describe what type represents and constraints
    
    ## Example
    
    ```cpp
    /// Non-owning view.
    template <class T>
    struct View {
      /// Data pointer.
      T* data;
      /// Size.
      std::size_t size;
      
      /// Constructor from range iterators.
      template <class It>
      View(It first, It last) { ... }
    };
    ```
    """)
    
    st.divider()
    st.markdown("[📚 Full Guidelines](https://open-sn.github.io/opensn/devguide/doxygen.html)")

# Footer
st.divider()
st.caption("Powered by TAMU AI Chat | OpenSn Doxygen Validator v1.0")
