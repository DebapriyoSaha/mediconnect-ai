"""
Utility functions for visualizing LangGraph agent graphs.
"""

def show_graph(graph, xray=False, save_to_file=None):
    """
    Display or save a LangGraph mermaid diagram with fallback rendering.
    
    Args:
        graph: The LangGraph object
        xray (bool): Whether to show internal graph details
        save_to_file (str): Optional filepath to save the PNG
        
    Returns:
        Image: IPython Image object (if save_to_file is None)
    """
    try:
        png_bytes = graph.get_graph(xray=xray).draw_mermaid_png()
    except Exception as e:
        print(f"Default renderer failed ({e}), falling back to pyppeteer...")
        import nest_asyncio
        nest_asyncio.apply()
        from langchain_core.runnables.graph import MermaidDrawMethod
        png_bytes = graph.get_graph(xray=xray).draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER)
    
    if save_to_file:
        with open(save_to_file, 'wb') as f:
            f.write(png_bytes)
        print(f"Graph saved to: {save_to_file}")
        return None
    else:
        from IPython.display import Image
        return Image(png_bytes)

def print_graph_ascii(graph, xray=False):
    """
    Print the graph structure as ASCII art to the console.
    
    Args:
        graph: The LangGraph object
        xray (bool): Whether to show internal graph details
    """
    try:
        print("\n=== AGENT GRAPH STRUCTURE (ASCII) ===\n")
        print(graph.get_graph(xray=xray).draw_ascii())
        print("\n=====================================\n")
    except Exception as e:
        print(f"Could not draw ASCII graph: {e}")
