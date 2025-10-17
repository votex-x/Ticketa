from flask import Flask, request, jsonify
from flask_cors import CORS
import discord
import asyncio
import os
from datetime import datetime
import threading

app = Flask(__name__)
CORS(app)

class SimpleDiscordAnalyzer:
    def __init__(self):
        self.active_tokens = {}
    
    async def analyze_server(self, token, guild_id):
        """Analisa servidor usando token temporário"""
        intents = discord.Intents.all()
        bot = discord.Client(intents=intents)
        
        result = {"error": "Não foi possível conectar"}
        event = asyncio.Event()
        
        @bot.event
        async def on_ready():
            try:
                print(f"Bot {bot.user} conectado!")
                guild = bot.get_guild(int(guild_id))
                
                if not guild:
                    result.update({"error": "Servidor não encontrado ou bot não está no servidor"})
                    event.set()
                    return
                
                # Coleta dados básicos
                members = guild.members
                bots = [m for m in members if m.bot]
                humans = [m for m in members if not m.bot]
                online = [m for m in humans if m.status != discord.Status.offline]
                
                result.update({
                    "success": True,
                    "server_info": {
                        "name": guild.name,
                        "id": str(guild.id),
                        "owner": str(guild.owner),
                        "created_at": guild.created_at.isoformat(),
                        "member_count": guild.member_count,
                        "icon_url": str(guild.icon.url) if guild.icon else None
                    },
                    "members": {
                        "total": len(members),
                        "humans": len(humans),
                        "bots": len(bots),
                        "online": len(online),
                        "breakdown": {
                            "humans_percentage": round((len(humans) / len(members)) * 100, 2),
                            "bots_percentage": round((len(bots) / len(members)) * 100, 2),
                            "online_percentage": round((len(online) / len(humans)) * 100, 2) if humans else 0
                        }
                    },
                    "channels": {
                        "text": len(guild.text_channels),
                        "voice": len(guild.voice_channels),
                        "categories": len(guild.categories),
                        "total": len(guild.channels)
                    },
                    "roles": {
                        "total": len(guild.roles),
                        "top_roles": [
                            {"name": role.name, "members": len(role.members)} 
                            for role in sorted(guild.roles, key=lambda x: len(x.members), reverse=True)[:10]
                        ]
                    },
                    "analysis_time": datetime.now().isoformat()
                })
                
            except Exception as e:
                result.update({"error": f"Erro na análise: {str(e)}"})
            finally:
                event.set()
        
        @bot.event
        async def on_error(event, *args, **kwargs):
            result.update({"error": f"Erro no bot: {event}"})
            event.set()
        
        try:
            # Timeout de 15 segundos
            await asyncio.wait_for(bot.start(token), timeout=15.0)
        except asyncio.TimeoutError:
            result.update({"error": "Timeout - Bot demorou muito para conectar"})
        except Exception as e:
            result.update({"error": f"Erro de conexão: {str(e)}"})
        finally:
            if not bot.is_closed():
                await bot.close()
        
        await event.wait()
        return result

# Instância global
analyzer = SimpleDiscordAnalyzer()

def run_async_in_thread(coro):
    """Executa corotina em thread separada"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/')
def home():
    return jsonify({
        "message": "🚀 Discord Public API - FIXED",
        "status": "online",
        "endpoints": {
            "POST /api/analyze": "Analisar servidor",
            "GET /api/health": "Status da API"
        },
        "example": {
            "method": "POST",
            "url": "/api/analyze", 
            "body": {
                "token": "seu_token_aqui",
                "guild_id": "123456789"
            }
        }
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_server():
    """Endpoint principal corrigido"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Envie JSON no body"}), 400
        
        token = data.get('token', '').strip()
        guild_id = data.get('guild_id', '').strip()
        
        if not token:
            return jsonify({"error": "Token é obrigatório"}), 400
        
        if not guild_id:
            return jsonify({"error": "guild_id é obrigatório"}), 400
        
        # Validação básica
        if not token.startswith('MT') or len(token) < 50:
            return jsonify({"error": "Token inválido"}), 400
        
        # Executa análise em thread separada
        result = run_async_in_thread(
            analyzer.analyze_server(token, guild_id)
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": f"Erro interno: {str(e)}",
            "tip": "Verifique se o token e guild_id estão corretos"
        }), 500

@app.route('/api/analyze/get', methods=['GET'])
def analyze_get():
    """Versão GET para teste rápido"""
    token = request.args.get('token', '')
    guild_id = request.args.get('guild_id', '')
    
    if not token or not guild_id:
        return jsonify({
            "error": "Use: /api/analyze/get?token=SEU_TOKEN&guild_id=123456789"
        })
    
    result = run_async_in_thread(
        analyzer.analyze_server(token, guild_id)
    )
    
    return jsonify(result)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Discord Public API"
    })

@app.route('/api/test', methods=['GET'])
def test():
    """Endpoint de teste simples"""
    return jsonify({
        "message": "API está funcionando!",
        "next_step": "Use POST /api/analyze com seu token"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)                "position": channel.position
            }
            
            if isinstance(channel, discord.TextChannel):
                channel_data["type"] = "text"
                channel_data["nsfw"] = channel.nsfw
                text_channels.append(channel_data)
            elif isinstance(channel, discord.VoiceChannel):
                channel_data["type"] = "voice"
                channel_data["members_in_voice"] = len(channel.members)
                voice_channels.append(channel_data)
        
        # Análise de emojis
        emojis_analysis = {
            "static": [{"name": e.name, "url": str(e.url)} for e in guild.emojis if not e.animated],
            "animated": [{"name": e.name, "url": str(e.url)} for e in guild.emojis if e.animated],
            "total": len(guild.emojis),
            "limits": {
                "max_emojis": guild.emoji_limit,
                "available_slots": guild.emoji_limit - len(guild.emojis)
            }
        }
        
        # Estatísticas de engajamento
        member_activity = {
            "online": len(online_members),
            "idle": len([m for m in members if m.status == discord.Status.idle]),
            "dnd": len([m for m in members if m.status == discord.Status.dnd]),
            "offline": len([m for m in members if m.status == discord.Status.offline])
        }
        
        # Cálculos de porcentagem
        total_humans = len(humans)
        engagement_percentage = round((len(online_members) / total_humans * 100), 2) if total_humans > 0 else 0
        
        return {
            "server_info": {
                "name": guild.name,
                "id": str(guild.id),
                "owner": {
                    "name": str(guild.owner),
                    "id": str(guild.owner.id)
                } if guild.owner else None,
                "created_at": guild.created_at.isoformat(),
                "icon_url": str(guild.icon.url) if guild.icon else None,
                "banner_url": str(guild.banner.url) if guild.banner else None,
                "description": guild.description,
                "verification_level": str(guild.verification_level),
                "premium_tier": guild.premium_tier,
                "boost_count": guild.premium_subscription_count
            },
            "members": {
                "total": len(members),
                "humans": len(humans),
                "bots": len(bots),
                "activity": member_activity,
                "breakdown": {
                    "humans_percentage": round((len(humans) / len(members)) * 100, 2),
                    "bots_percentage": round((len(bots) / len(members)) * 100, 2)
                }
            },
            "engagement": {
                "online_percentage": engagement_percentage,
                "activity_score": self.calculate_activity_score(member_activity),
                "health_status": "healthy" if engagement_percentage > 30 else "moderate" if engagement_percentage > 15 else "low"
            },
            "channels": {
                "text": {
                    "count": len(text_channels),
                    "list": text_channels[:10]  # Limita para não ficar muito grande
                },
                "voice": {
                    "count": len(voice_channels),
                    "list": voice_channels[:10]
                },
                "categories": len(guild.categories),
                "total": len(guild.channels)
            },
            "roles": {
                "total": len(guild.roles),
                "list": roles_analysis[:15],  # Limita para não ficar muito grande
                "hierarchy": [role.name for role in sorted(guild.roles, key=lambda x: x.position, reverse=True)][:10]
            },
            "emojis": emojis_analysis,
            "features": {
                "server_features": list(guild.features),
                "premium_features": [
                    "banner" if guild.banner else None,
                    "vanity_url" if guild.vanity_url else None,
                    "boosted" if guild.premium_tier > 0 else None
                ]
            },
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def calculate_activity_score(self, activity):
        """Calcula score de atividade baseado nos membros online"""
        total_active = activity["online"] + activity["idle"] + activity["dnd"]
        return min(100, round((total_active / max(1, activity["offline"])) * 100, 2))

# Instância global do gerenciador
bot_manager = DiscordBotManager()

# Rotas da API Pública
@app.route('/')
def home():
    return jsonify({
        "message": "🚀 Discord Public Analytics API",
        "version": "2.0.0",
        "description": "API 100% pública - Cada bot usa seu próprio token",
        "endpoints": {
            "server_analysis": "POST /api/analyze",
            "health_check": "GET /api/health",
            "docs": "GET /api/docs"
        },
        "usage_example": {
            "method": "POST",
            "url": "/api/analyze",
            "body": {
                "token": "SEU_BOT_TOKEN",
                "guild_id": "123456789"
            }
        }
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_server():
    """Endpoint principal - Análise completa do servidor"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "JSON body é obrigatório"}), 400
        
        token = data.get('token')
        guild_id = data.get('guild_id')
        
        if not token or not guild_id:
            return jsonify({
                "error": "Token e guild_id são obrigatórios",
                "received": {
                    "token_provided": bool(token),
                    "guild_id_provided": bool(guild_id)
                }
            }), 400
        
        # Executa a análise de forma assíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                bot_manager.get_guild_data(token, guild_id)
            )
            return jsonify(result)
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check da API"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Discord Public Analytics API",
        "version": "2.0.0"
    })

@app.route('/api/docs', methods=['GET'])
def api_docs():
    """Documentação interativa da API"""
    return jsonify({
        "documentation": "Discord Public Analytics API - Docs",
        "base_url": "https://sua-api.herokuapp.com",
        "authentication": "Cada request envia o token do bot no body",
        "endpoints": {
            "POST /api/analyze": {
                "description": "Análise completa de um servidor Discord",
                "parameters": {
                    "token": "Token do bot Discord (obrigatório)",
                    "guild_id": "ID do servidor (obrigatório)"
                },
                "example_request": {
                    "token": "seu_bot_token_aqui",
                    "guild_id": "123456789012345678"
                },
                "example_response": "Inclui dados de membros, canais, cargos, emojis, etc."
            },
            "GET /api/health": {
                "description": "Status da API"
            }
        },
        "rate_limiting": "Sem limites para uso público (use com responsabilidade)",
        "open_source": "https://github.com/seu-usuario/discord-public-api"
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint não encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)      } catch (e) {
        return addLog('Embed fields JSON inválido.');
      }
    }
    // push command into Firebase Realtime DB under /commands/<guildId>/<uuid>
    const cmdId = Math.random().toString(36).slice(2,10);
    const path = `/commands/${guildId}/${cmdId}`;
    await firebase.database().ref(path).set(payload);
    addLog('Pedido enviado: ' + cmdId);
  } catch (e) {
    console.error(e);
    addLog('Erro ao enviar pedido: ' + e.message);
  }
});
